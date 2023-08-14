#!/usr/bin/env python3
"""
Simple API webserver for testing and logging.
(C) 2023, P5 Software, LLC
"""
import http.server
import socketserver
import logging
import logging.handlers as handlers
import signal
import json
import os
import sys
import sqlite3
import time
from watchdog.observers import Observer             #pip3 install watchdog
from watchdog.events import PatternMatchingEventHandler
import random
from mimetypes import guess_extension


def handle_interrupt(signal, frame):
    raise sigKill("SIGKILL Requested")


class sigKill(Exception):
    pass


def responseHandler(requestHandler:http.server.BaseHTTPRequestHandler, status, headers=[], body=None, contentType="application/json"):

    #Send the HTTP status code requested
    requestHandler.send_response(status)

    if status == 404:
        contentType = None

    if contentType != None and body != None:
        tmpHeader = {}
        tmpHeader['key'] = "Content-Type"
        tmpHeader['value'] = contentType
        headers.append(tmpHeader)

    tmpHeader = {}
    tmpHeader['key'] = 'Access-Control-Allow-Origin'
    tmpHeader['value'] = "*"
    headers.append(tmpHeader)

    #Send each header to the caller
    for header in headers:
        requestHandler.send_header(header['key'], header['value'])

    #Send a blank line to the caller
    requestHandler.end_headers()

    #Empty the headers
    headers.clear()

    #Write the response body to the caller
    if body is not None:
        if type(body) in [dict, list]:
            requestHandler.wfile.write(json.dumps(body).encode("utf8"))
            return

        requestHandler.wfile.write(body)
        return


class RequestHandler(http.server.SimpleHTTPRequestHandler):

    #Create a conversation tracker for this request
    def __init__(self, request, client_address, server):
        http.server.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)


    def log_message(self, format, *args):
        #Quiet the logs
        return


    def do_POST(self):
        self.handler()

        
    def do_OPTIONS(self):

        tmpHeaders = []

        tmpHeader = {}
        tmpHeader['key'] = 'Access-Control-Allow-Methods'
        tmpHeader['value'] = "*"
        tmpHeaders.append(tmpHeader)

        tmpHeader = {}
        tmpHeader['key'] = 'Access-Control-Allow-Headers'
        tmpHeader['value'] = "*"
        tmpHeaders.append(tmpHeader)

        responseHandler(self, 200, headers=tmpHeaders)


    def do_GET(self):
        self.handler()


    def do_DELETE(self):
        self.handler()


    def do_PUT(self):
        self.handler()


    def do_PATCH(self):
        self.handler()


    def handler(self):

        self.close_connection = True

        try:

            #Check if the request exists here
            database.row_factory = sqlite3.Row
            dbCursor = database.cursor()

            query = "SELECT * FROM endpoints WHERE method=? AND path=?"
            parameters = (self.command, self.path)

            dbCursor.execute(query, parameters)
            rows = dbCursor.fetchall()
            dbCursor.close()

            if len(rows) < 1:
                responseHandler(self, 404)
                return
            
            rowNumber = 0        

            if len(rows) > 1:
                rowNumber = random.randint(0, len(rows)-1)

            if rows[rowNumber]['request_file_path'] != None and self.command in ["POST", "PATCH", "PUT"]:
                extension = guess_extension(self.headers['Content-Type'])
                content_length = int(self.headers['Content-Length'])

                if extension == None:
                    extension = ""

                with open(os.path.join(rows[rowNumber]['request_file_path'], str(int(time.time()*1000))) + extension,  "wb") as f:
                    f.write(self.rfile.read(content_length))
                    f.close()

            time.sleep(rows[rowNumber]['delay']/1000)

            if rows[rowNumber]['response_code'] == 0:
                return

            if rows[rowNumber]['response_file'] == None:
                 responseHandler(self, rows[rowNumber]['response_code'])
                 return
            
            if os.path.exists(rows[rowNumber]['response_file']) == False:
                raise HTTPErrorResponse(message="File specified in settings.json (" + rows[rowNumber]['response_file'] + ") does not exist.")
                return
                
            with open(rows[rowNumber]['response_file'], "rb") as f:
                contentType = self.guess_type(rows[rowNumber]['response_file'])
                data = f.read()
                f.close()

            responseHandler(self, rows[rowNumber]['response_code'], body=data, contentType=contentType)

                   
        except HTTPErrorResponse as ex:
            responseHandler(self, ex.status, body={"error": ex.message})

        except Exception as ex:
            logger.error({"exception": ex})
            responseHandler(self, 500, body={"error": "Unknown Error"})


class HTTPErrorResponse(Exception):

    #Custom error message wrapper
    def __init__(self, status=500, message="Unknown Error"):
        self.status = status
        self.message = message
        super().__init__(self.status, self.message)

   
def exitApp(exitCode=None):

    #Force the log level to info
    logger.setLevel(logging.INFO)

    if exitCode is None:
        exitCode = 0

    if exitCode == 0:
        logger.info(__file__ + " finished successfully.")

    if exitCode != 0:
        logger.info("Error; Exiting with code " + str(exitCode))

    sys.exit(exitCode)


def main():
    global settings

    #Start the HTTP server
    try:

        if "port" not in settings:
            raise Exception("Error while reading settings.")

        logger.info("Starting HTTP server on port " + str(settings['port']))

        #Create the webserver
        httpd = socketserver.ThreadingTCPServer(("", int(settings['port'])), RequestHandler)

        logger.info((__file__) + " started.")

        #Serve clients until stopped
        httpd.serve_forever()

    except sigKill:
        #Kill the http server and clean up open connections
        httpd.server_close()
        exitApp(0)       

    except KeyboardInterrupt:
        #Kill the http server and clean up open connections
        httpd.server_close()
        exitApp(0)

    except Exception as ex:
        logger.error(ex)
        exitApp(1)


def loadEndpoints():
    global settings
    global settings_file_name

    logger.info("Loading settings.")

    if os.path.exists(settings_file_name) == False:
        raise Exception ("settings.json does not exist.")
    
    try:
        settings = json.load(open(settings_file_name))

    except json.JSONDecodeError as ex:
        logger.error("Error while decoding settings.json: '" + ex.msg + "'.\nIf the server has already started, the previous configuration will continue to be used.")
        return

    if "port" not in settings:
        settings['port'] = 8080

    if str(settings['port']).isnumeric() != True:
        raise Exception ("Invalid 'port' in settings.json")
        return

    if "endpoints" not in settings:
        raise Exception ("Missing object 'endpoints' in settings.json")
        return
    
    if not isinstance(settings['endpoints'], list):
        raise Exception ("'endpoints' should be an array in settings.json")
        return

    cursor = database.cursor()
    cursor.execute("DELETE FROM endpoints;")

    position = -1

    for endpoint in settings['endpoints']:

        position = position + 1

        if "enabled" not in endpoint:
            endpoint['enabled'] = True

        if endpoint['enabled'] == False:
            continue

        if "method" not in endpoint:
            logger.warning("Missing 'method' for endpoint at position " + str(position) + ", skipping")
            continue

        if "path" not in endpoint:
            logger.warning("Missing 'path' for endpoint at position " + str(position) + ", skipping")
            continue

        if "response_file" in endpoint:
            endpoint['response_file'] = str(endpoint['response_file']).strip()

        if "response_file" not in endpoint:
            endpoint['response_file'] = None

        if "request_file_path" in endpoint:
            endpoint['request_file_path'] = str(endpoint['request_file_path']).strip()

        if "request_file_path" not in endpoint:
            endpoint['request_file_path'] = None

        if endpoint['request_file_path'] != None: 
            if os.path.exists(endpoint['request_file_path']) == False:
                os.makedirs(endpoint['request_file_path'])

        if "response_code" not in endpoint:
            endpoint['response_code'] = 200

        if str(endpoint['response_code']).isnumeric() != True:
            logger.warning("response_code at position " + str(position) + " " + endpoint['method'] + " " + endpoint['path'] + " is non-numeric, will use 200 instead")
            endpoint['response_code'] = 200

        if "delay" not in endpoint:
            endpoint['delay'] = 0

        if str(endpoint['delay']).isnumeric() != True:
            logger.warning("delay at position " + str(position) + " " + endpoint['method'] + " " + endpoint['path'] + " is non-numeric, will use 0 instead")
            endpoint['delay'] = 0

        insert_statement = "INSERT INTO endpoints (method, path, response_file, request_file_path, response_code, delay) VALUES (?,?,?,?,?,?)"
        parameters = (str(endpoint['method']).strip().upper(), str(endpoint['path']).strip(), endpoint['response_file'], endpoint['request_file_path'], endpoint['response_code'], endpoint['delay'])
        cursor.execute(insert_statement, parameters)

    logger.info("Settings loaded.")


class fileChanged(PatternMatchingEventHandler):

    def __init__(self):
        # Set the patterns for PatternMatchingEventHandler
        PatternMatchingEventHandler.__init__(self)
        

    def on_modified(self, event):
        if event.src_path == settings_file_name:
            loadEndpoints()


def setup():
    global logger
    global settings
    global database
    global settings_file_name

    settings = {}
    settings_file_name = ""
    
    try:

        logger = logging.getLogger((__file__))
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
        logHandler = handlers.RotatingFileHandler(os.path.join(os.path.realpath(os.path.dirname(__file__)), __file__ + '.log'), maxBytes=10485760, backupCount=1)
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)
        logger.setLevel(logging.INFO)

        settings_file_name = os.path.join(os.path.realpath(os.path.dirname(__file__)), "settings.json")

        logger.info("Setting up application.")

        database = sqlite3.connect(":memory:" , check_same_thread=False)
        cursor = database.cursor()
        cursor.execute("CREATE TABLE endpoints (method text, path text, response_file text, request_file_path text, response_code int, delay int);")
        cursor.close()

        loadEndpoints()

        observer = Observer()
        observer.schedule(fileChanged(), path=os.path.dirname(settings_file_name))
        observer.start()

        logger.info("Monitoring file " + settings_file_name)

    except Exception as ex:
        logger.error(ex)
        exitApp(1)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, handle_interrupt)
    setup()
    main()
# Simple API Webserver

A simple webserver to test API's

## What Does it Do?

This is a basic webserver that is intended to act as a stand-in for a real API.  It's useful when testing user interfaces that need to call an API and display results, but you don't want to break the API to test all the UI's edge cases.  The server will return back headers to support most CORS policies.

Some useful examples of things you can do:
 - Remove endpoint entirely by disabling
 - Multiple, random responses to an endpoint
 - Change HTTP response codes
 - Create long delays in responses
 - Socket hang-up without response
 - Content-Type response header testing

## What Doesn't it Do?

A bunch of things, though here are a few that could be added:
 - Authentication validation
 - ~~Logging requests or payloads~~
 - Intelligent responses based on request content
 - Non-core HTTP method types
 - CORS header verification
 - Header manipulation

## Pre-requisites

### Watchdog

Install via pip3:

`pip3 install watchdog`

## Usage

Simply launch the webserver via Python.  Note, a settings.json file must be present in the same directory where the script is located.

`python3 api-webserver.py`

## Settings Configuration

The settings.json file must be present in the same directory as where the script is located.  At a minimum, `endpoints` must exist in the settings.json file.  For example, this is the minimum file that is allowed, though the webserver will respond with a 404 on all requests to it with this configuration:

```
{
    "endpoints": []
}
```

Server will automatically pick up changes made to the settings.json file while running.  *Changing the port is not permitted after starting the server.*

| Parameter | Default | Required | Data Type | Description |
|-----------|---------|----------|-----------|-------------|
| port | 8080 | Optional | Integer | Defines the HTTP port the sever should use when starting |
| endpoints | | Required | Array | The collection of endpoints the server should observe |
| endpoints -> method | (None) | Required | String | The HTTP method for the request.  Supported are (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`). Note, `OPTIONS` always returns 200 with headers to support CORS; This cannot be overridden.
| endpoints -> path | (None) | Required | String | The URL path of the request, inclusive of the leading slash.|
| endpoints -> response_file | (None) | Optional | String | File path containing the response body that will be sent when the request is processed.  The content-type is guessed based on the file extension. If not specified, no body will be sent.|
| endpoints -> request_file_path | (None) | Optional | String | Path where the request payload should be saved on `POST`, `PUT`, `PATCH` operations.  Timestamp will be used for the filename, and the file extension will be guessed from the Content-Type header. If not specified, the payload will not be saved.|
| endpoints-> response_code | `200` | Optional | Integer | The HTTP response code that will be returned to the caller.  Any response code can be specified. Setting the value to `0` will cause a socket hang-up without a response.|
| endpoints -> delay | `0` | Optional | Integer | The number of *milliseconds* the server should wait before processing a response.|
| endpoints -> enabled | `true` | Optional | Boolean | If this entry for the endpoint is should be enabled for responses.|




### Examples

#### Disabling a GET endpoint /foo/bar
```
{
    "endpoints": [
        {
            "method": "GET",
            "path": "/foo/bar",
            "enabled": false
        }
}
``` 

#### Returning a file with a POST response after waiting 150ms
```
{
    "endpoints": [
        {
            "method": "POST",
            "path": "/foo/bar",
            "response_file": "/foo/bar/myfile.txt",
            "delay": 150
        }
    ]
}
```

#### Randomly returning either a file with a POST response after waiting 150ms or the "I'm a teapot" Response immediately
```
{
    "endpoints": [
        {
            "method": "POST",
            "path": "/foo/bar",
            "response_file": "/foo/bar/myfile.txt",
            "delay": 150
        },
        {
            "method": "POST",
            "path": "/foo/bar",
            "response_code": 418
        }
    ]
}
```
import contextlib
import copy
import logging
import requests
import sys
from flask import Request
from pypomes_core import APP_PREFIX, env_get_int, exc_format
from pypomes_security import access_get_token
from requests import Response
from typing import Any, Final

from .http_statuses import _HTTP_STATUSES

HTTP_DELETE_TIMEOUT: Final[int] = env_get_int(f"{APP_PREFIX}_HTTP_DELETE_TIMEOUT", 300)
HTTP_GET_TIMEOUT: Final[int] = env_get_int(f"{APP_PREFIX}_HTTP_GET_TIMEOUT", 300)
HTTP_HEAD_TIMEOUT: Final[int] = env_get_int(f"{APP_PREFIX}_HTTP_HEAD_TIMEOUT", 300)
HTTP_PATCH_TIMEOUT: Final[int] = env_get_int(f"{APP_PREFIX}_HTTP_POST_TIMEOUT", 300)
HTTP_POST_TIMEOUT: Final[int] = env_get_int(f"{APP_PREFIX}_HTTP_POST_TIMEOUT", 300)
HTTP_PUT_TIMEOUT: Final[int] = env_get_int(f"{APP_PREFIX}_HTTP_PUT_TIMEOUT", 300)

MIMETYPE_BINARY: Final[str] = "application/octet-stream"
MIMETYPE_CSS: Final[str] = "text/css"
MIMETYPE_CSV: Final[str] = "text/csv"
MIMETYPE_HTML: Final[str] = "text/html"
MIMETYPE_JAVASCRIPT: Final[str] = "text/javascript"
MIMETYPE_JSON: Final[str] = "application/json"
MIMETYPE_MULTIPART: Final[str] = "multipart/form-data"
MIMETYPE_PDF: Final[str] = "application/pdf"
MIMETYPE_PKCS7: Final[str] = "application/pkcs7-signature"
MIMETYPE_SOAP: Final[str] = "application/soap+xml"
MIMETYPE_TEXT: Final[str] = "text/plain"
MIMETYPE_URLENCODED: Final[str] = "application/x-www-form-urlencoded"
MIMETYPE_XML: Final[str] = "application/xml"
MIMETYPE_ZIP: Final[str] = "application/zip"


def http_status_code(status_name: str) -> int:
    """
    Return the corresponding code of the HTTP status *status_name*.

    :param status_name: the name of HTTP status
    :return: the corresponding HTTP status code
    """
    # initialize the return variable
    result: int | None = None

    for key, value in _HTTP_STATUSES:
        if status_name == value["name"]:
            result = key

    return result


def http_status_name(status_code: int) -> str:
    """
    Return the corresponding name of the HTTP status *status_code*.

    :param status_code: the code of the HTTP status
    :return: the corresponding HTTP status name
    """
    item: dict = _HTTP_STATUSES.get(status_code)
    return (item or {"name": "Unknown status code"}).get("name")


def http_status_description(status_code: int,
                            lang: str = "en") -> str:
    """
    Return the description of the HTTP status *status_code*.

    :param status_code: the code of the HTTP status
    :param lang: optional language ('en' or 'pt' - defaults to 'en')
    :return: the corresponding HTTP status description, in the given language
    """
    item: dict = _HTTP_STATUSES.get(status_code)
    return (item or {"en": "Unknown status code", "pt": "Status desconhecido"}).get(lang)


def http_get_parameter(request: Request,
                       param: str) -> Any:
    """
    Obtain the *request*'s input parameter named *param_name*.

    Until *param* is found, the following are sequentially attempted:
        - elements in a HTML form
        - parameters in the URL's query part
        - key/value pairs in a *JSON* structure in the request's body

    :param request: the Request object
    :param param: name of parameter to retrieve
    :return: the parameter's value, or 'None' if not found
    """
    # initialize the return variable
    result: Any = None

    # look for parameter in form
    params: dict = request.form
    if params:
        result = params.get(param)

    # was it found ?
    if result is None:
        # no, look for parameter in the URL query
        # ruff: noqa: PD011
        params = request.values
        if params:
            result = params.get(param)

    # was it found ?
    if result is None:
        # no, look for parameter in the JSON data
        with contextlib.suppress(Exception):
            params = request.get_json()
            if params:
                result = params.get(param)

    return result


def http_get_parameters(request: Request) -> dict:
    """
    Obtain the *request*'s input parameters.

    The following are cumulatively attempted, in sequence:
        - key/value pairs in a *JSON* structure in the request's body
        - parameters in the URL's query part
        - elements in a HTML form

    :param request: the Request object
    :return: dict containing the input parameters (empty, if no input data exists)
    """
    # initialize the return variable
    result: dict = {}

    # attempt to retrieve the JSON data in body
    with contextlib.suppress(Exception):
        result.update(request.get_json())

    # obtain parameters in URL query
    result.update(request.values)

    # obtain parameters in form
    result.update(request.form)

    return result


def http_delete(errors: list[str] | None,
                url: str,
                headers: dict = None,
                params: dict = None,
                data: dict = None,
                json: dict = None, auth: str = None,
                timeout: int | None = HTTP_DELETE_TIMEOUT,
                logger: logging.Logger = None) -> Response:
    """
    Issue a *DELETE* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_DELETE_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the DELETE operation
    """
    return _http_rest(errors, "DELETE", url, headers, params, data, json, auth, timeout, logger)


def http_get(errors: list[str] | None,
             url: str,
             headers: dict = None,
             params: dict = None,
             data: dict = None,
             json: dict = None, auth: str = None,
             timeout: int | None = HTTP_GET_TIMEOUT,
             logger: logging.Logger = None) -> Response:
    """
    Issue a *GET* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_GET_TIMEOUT - use None to omit)
    :param logger: optional logger
    :return: the response to the GET operation
    """
    return _http_rest(errors, "GET", url, headers,
                      params, data, json, auth, timeout, logger)


def http_head(errors: list[str] | None,
              url: str,
              headers: dict = None,
              params: dict = None,
              data: dict = None,
              json: dict = None, auth: str = None,
              timeout: int | None = HTTP_HEAD_TIMEOUT,
              logger: logging.Logger = None) -> Response:
    """
    Issue a *HEAD* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_GET_TIMEOUT - use None to omit)
    :param logger: optional logger
    :return: the response to the GET operation
    """
    return _http_rest(errors, "HEAD", url, headers,
                      params, data, json, auth, timeout, logger)


def http_patch(errors: list[str] | None,
               url: str,
               headers: dict = None,
               params: dict = None,
               data: dict = None,
               json: dict = None, auth: str = None,
               timeout: int | None = HTTP_PATCH_TIMEOUT,
               logger: logging.Logger = None) -> Response:
    """
    Issue a *PATCH* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_PATCH_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the PATCH operation
    """
    return _http_rest(errors, "POST", url, headers,
                      params, data, json, auth, timeout, logger)


def http_post(errors: list[str] | None,
              url: str,
              headers: dict = None,
              params: dict = None,
              data: dict = None,
              json: dict = None,
              auth: str = None,
              timeout: int | None = HTTP_POST_TIMEOUT,
              logger: logging.Logger = None) -> Response:
    """
    Issue a *POST* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_POST_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the POST operation
    """
    return _http_rest(errors, "POST", url, headers,
                      params, data, json, auth, timeout, logger)


def http_put(errors: list[str] | None,
             url: str,
             headers: dict = None,
             params: dict = None,
             data: dict = None,
             json: dict = None,
             auth: str = None,
             timeout: int | None = HTTP_PUT_TIMEOUT,
             logger: logging.Logger = None) -> Response:
    """
    Issue a *PUT* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_POST_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the PUT operation
    """
    return _http_rest(errors, "PUT", url, headers,
                      params, data, json, auth, timeout, logger)


def _http_rest(errors: list[str],
               method: str,
               url: str,
               headers: dict,
               params: dict,
               data: dict | None,
               json: dict | None,
               auth: str | None,
               timeout: int,
               logger: logging.Logger) -> Response:
    """
    Issue a *REST* request to the given *url*, and return the response received.

    The returned response might be *None*.
    The request might contain *headers* and *parameters*.

    :param errors: incidental error messages
    :param method: the REST method to use (DELETE, GET, HEAD, PATCH, POST or PUT)
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param auth: optional authentication scheme to use
    :param timeout: timeout, in seconds (defaults to HTTP_POST_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the REST operation
    """
    # initialize the return variable
    result: Response | None = None

    # clone the headers object (it accepts None)
    op_headers: dict = copy.copy(headers)

    # initialize the error message
    err_msg: str | None = None

    if logger:
        logger.debug(f"{method} '{url}'")

    try:
        # initialize the local errors list
        op_errors: list[str] = []

        # satisfy authorization requirements, if applicable
        if auth:
            if auth.startswith("bearer:"):
                # request authentiation token
                token: str = access_get_token(errors=op_errors,
                                              service_url=auth[7:],
                                              logger=logger,
                                              timeout=timeout)
                if len(op_errors) == 0:
                    if not op_headers:
                        op_headers = {}
                    op_headers["Authorization"] = f"Bearer {token}"
                elif errors is not None:
                    errors.extend(op_errors)
            else:
                err_msg = f"Authentication scheme '{auth}' not implemented"

        # were there errors ?
        if not err_msg and not op_errors:
            # no, send the REST request
            match method:
                case "DELETE":
                    result = requests.delete(url=url,
                                             headers=op_headers,
                                             params=params,
                                             data=data,
                                             json=json,
                                             timeout=timeout)
                case "GET":
                    result = requests.get(url=url,
                                          headers=op_headers,
                                          params=params,
                                          data=data,
                                          json=json,
                                          timeout=timeout)
                case "HEAD":
                    result = requests.head(url=url,
                                           headers=op_headers,
                                           params=params,
                                           data=data,
                                           json=json,
                                           timeout=timeout)
                case "PATCH":
                    result = requests.patch(url=url,
                                            headers=op_headers,
                                            params=params,
                                            data=data,
                                            json=json,
                                            timeout=timeout)
                case "POST":
                    result = requests.post(url=url,
                                           headers=op_headers,
                                           params=params,
                                           data=data,
                                           json=json,
                                           timeout=timeout)
                case "PUT":
                    result = requests.put(url=url,
                                          headers=op_headers,
                                          params=params,
                                          data=data,
                                          json=json,
                                          timeout=timeout)
            if logger:
                logger.debug(f"{method} '{url}': "
                             f"status {result.status_code} ({http_status_name(result.status_code)})")

            # was the request successful ?
            if result.status_code not in [200, 201, 202, 203]:
                # no, report the problem
                err_msg = (
                    f"{method} '{url}': failed, "
                    f"status {result.status_code}, reason '{result.reason}'"
                )
    except Exception as e:
        # the operation raised an exception
        err_msg = (
            f"{method} '{url}': error, "
            f"'{exc_format(e, sys.exc_info())}'"
        )

    # is there an error message ?
    if err_msg:
        # yes, log and/or save it
        if logger:
            logger.error(err_msg)
        if errors is not None:
            errors.append(err_msg)

    return result

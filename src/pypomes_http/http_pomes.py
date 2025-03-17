import contextlib
import requests
import sys
from enum import StrEnum
from flask import Request
from logging import Logger
from io import BytesIO
from pypomes_core import APP_PREFIX, env_get_float, exc_format
from requests import Response
from typing import Any, Final, Literal, BinaryIO

from .http_statuses import _HTTP_STATUSES

HTTP_DELETE_TIMEOUT: Final[float] = env_get_float(key=f"{APP_PREFIX}_HTTP_DELETE_TIMEOUT",
                                                  def_value=300.)
HTTP_GET_TIMEOUT: Final[float] = env_get_float(key=f"{APP_PREFIX}_HTTP_GET_TIMEOUT",
                                               def_value=300.)
HTTP_HEAD_TIMEOUT: Final[float] = env_get_float(key=f"{APP_PREFIX}_HTTP_HEAD_TIMEOUT",
                                                def_value=300.)
HTTP_PATCH_TIMEOUT: Final[float] = env_get_float(key=f"{APP_PREFIX}_HTTP_POST_TIMEOUT",
                                                 def_value=300.)
HTTP_POST_TIMEOUT: Final[float] = env_get_float(key=f"{APP_PREFIX}_HTTP_POST_TIMEOUT",
                                                def_value=300.)
HTTP_PUT_TIMEOUT: Final[float] = env_get_float(key=f"{APP_PREFIX}_HTTP_PUT_TIMEOUT",
                                               def_value=300.)


class HttpMethod(StrEnum):
    """
    HTTP methods.
    """
    DELETE = "DELETE"
    GET = "GET"
    HEAD = "HEAD"
    PATCH = "PATH"
    POST = "POST"
    PUT = "PUT"


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
                            lang: Literal["en", "pt"] = "en") -> str:
    """
    Return the description of the HTTP status *status_code*.

    :param status_code: the code of the HTTP status
    :param lang: optional language ('en' or 'pt' - defaults to 'en')
    :return: the corresponding HTTP status description, in the given language
    """
    item: dict = _HTTP_STATUSES.get(status_code)
    return (item or {"en": "Unknown status code", "pt": "Status desconhecido"}).get(lang)


def http_retrieve_parameters(url: str) -> dict[str, str]:
    """
    Retrieve and return the parameters in the query string of *url*.

    :param url: the url to retrieve parameters from
    :return: the extracted parameters, or an empty *dict* if no parameters were found
    """
    # initialize the return variable
    result: dict[str, str] = {}

    # retrieve the parameters
    pos: int = url.find("?")
    if pos > 0:
        params: list[str] = url[pos + 1:].split(sep="&")
        for param in params:
            key: str = param.split("=")[0]
            value: str = param.split("=")[1]
            result[key] = value

    return result


def http_get_parameter(request: Request,
                       param: str,
                       sources: list[str] = None) -> Any:
    """
    Obtain the *request*'s input parameter named *param_name*.

    The following are cumulatively attempted, in the sequence defined by *sources*, defaulting to:
        1. key/value pairs in a *JSON* structure in the request's body
        2. parameters in the URL's query string
        3. elements in a HTML form

    :param request: the Request object
    :param sources: the sequence of sources to inspect (defaults to *['body', 'query', 'form']*)
    :param param: name of parameter to retrieve
    :return: the parameter's value, or 'None' if not found
    """
    # initialize the return variable
    result: Any = None

    # establish the default sequence
    sources = sources or ["body", "query", "form"]

    for source in reversed(sources):
        # attempt to retrieve the JSON data in body
        params: dict[str, Any] | None = None
        match source:
            case "query":
                # obtain parameters in URL query
                params = request.values
            case "body":
                # obtain parameter in the JSON data
                with contextlib.suppress(Exception):
                    params = request.get_json()
            case "form":
                # obtain parameters in form
                params = request.form
        if params:
            result = params.get(param)
            if result:
                break

    return result


def http_get_parameters(request: Request,
                        sources: list[str] = None) -> dict[str, Any]:
    """
    Obtain the *request*'s input parameters.

    The following are cumulatively attempted, in the sequence defined by *sources*, defaulting to:
        1. key/value pairs in a *JSON* structure in the request's body
        2. parameters in the URL's query string
        3. elements in a HTML form

    :param request: the Request object
    :param sources: the sequence of sources to inspect (defaults to *['body', 'query', 'form']*)
    :return: dict containing the input parameters (empty, if no input data exists)
    """
    # initialize the return variable
    result: dict[str, Any] = {}

    # establish the default sequence
    sources = sources or ["body", "query", "form"]

    for source in reversed(sources):
        # attempt to retrieve the JSON data in body
        match source:
            case "query":
                # obtain parameters in URL query
                result.update(request.values)
            case "body":
                with contextlib.suppress(Exception):
                    result.update(request.get_json())
            case "form":
                # obtain parameters in form
                result.update(request.form)

    return result


def http_delete(errors: list[str] | None,
                url: str,
                headers: dict[str, str] = None,
                params: dict[str, Any] = None,
                data: dict[str, Any] = None,
                json: dict[str, Any] = None,
                timeout: float | None = HTTP_DELETE_TIMEOUT,
                logger: Logger = None) -> Response:
    """
    Issue a *DELETE* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param timeout: request timeout, in seconds (defaults to HTTP_DELETE_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the DELETE operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method=HttpMethod.DELETE,
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     timeout=timeout,
                     logger=logger)


def http_get(errors: list[str] | None,
             url: str,
             headers: dict[str, str] = None,
             params: dict[str, Any] = None,
             data: dict[str, Any] = None,
             json: dict[str, Any] = None,
             timeout: float | None = HTTP_GET_TIMEOUT,
             logger: Logger = None) -> Response:
    """
    Issue a *GET* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param timeout: request timeout, in seconds (defaults to HTTP_GET_TIMEOUT - use None to omit)
    :param logger: optional logger
    :return: the response to the GET operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method=HttpMethod.GET,
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     timeout=timeout,
                     logger=logger)


def http_head(errors: list[str] | None,
              url: str,
              headers: dict[str, str] = None,
              params: dict[str, Any] = None,
              data: dict[str, Any] = None,
              json: dict[str, Any] = None,
              timeout: float | None = HTTP_HEAD_TIMEOUT,
              logger: Logger = None) -> Response:
    """
    Issue a *HEAD* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param timeout: request timeout, in seconds (defaults to HTTP_HEAD_TIMEOUT - use None to omit)
    :param logger: optional logger
    :return: the response to the HEAD operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method=HttpMethod.HEAD,
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     timeout=timeout,
                     logger=logger)


def http_patch(errors: list[str] | None,
               url: str,
               headers: dict[str, str] = None,
               params: dict[str, Any] = None,
               data: dict[str, Any] = None,
               json: dict[str, Any] = None,
               timeout: float | None = HTTP_PATCH_TIMEOUT,
               logger: Logger = None) -> Response:
    """
    Issue a *PATCH* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param timeout: request timeout, in seconds (defaults to HTTP_PATCH_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the PATCH operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method=HttpMethod.PATCH,
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     timeout=timeout,
                     logger=logger)


def http_post(errors: list[str] | None,
              url: str,
              headers: dict[str, str] = None,
              params: dict[str, Any] = None,
              data: dict[str, Any] = None,
              json: dict[str, Any] = None,
              files: (dict[str, bytes | BinaryIO] |
                      dict[str, tuple[str, bytes | BinaryIO]] |
                      dict[str, tuple[str, bytes | BinaryIO, str]] |
                      dict[str, tuple[str, bytes | BinaryIO, str, dict[str, Any]]]) = None,
              timeout: float | None = HTTP_POST_TIMEOUT,
              logger: Logger = None) -> Response:
    """
    Issue a *POST* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    To send multipart-encoded files, the optional *files* parameter is used, formatted as
    a *dict* holding pairs of *name* and:
      - a *file-content*, or
      - a *tuple* holding *file-name, file-content*, or
      - a *tuple* holding *file-name, file-content, content-type*, or
      - a *tuple* holding *file-name, file-content, content-type, custom-headers*
    These parameter elements are:
      - *file-name*: the name of the file
      _ *file-content*: the file contents, or a pointer obtained from *Path.open()* or *BytesIO*
      - *content-type*: the mimetype of the file
      - *custom-headers*: a *dict* containing additional headers for the file

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param files: optionally, one or more files to send
    :param timeout: request timeout, in seconds (defaults to HTTP_POST_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the POST operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method=HttpMethod.POST,
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     files=files,
                     timeout=timeout,
                     logger=logger)


def http_put(errors: list[str] | None,
             url: str,
             headers: dict[str, str] = None,
             params: dict[str, Any] = None,
             data: dict[str, Any] = None,
             json: dict[str, Any] = None,
             timeout: float | None = HTTP_PUT_TIMEOUT,
             logger: Logger = None) -> Response:
    """
    Issue a *PUT* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    :param errors: incidental error messages
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param timeout: request timeout, in seconds (defaults to HTTP_PUT_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the PUT operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method=HttpMethod.PUT,
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     timeout=timeout,
                     logger=logger)


def http_rest(errors: list[str],
              method: HttpMethod,
              url: str,
              headers: dict[str, str] = None,
              params: dict[str, Any] = None,
              data: dict[str, Any] = None,
              json: dict[str, Any] = None,
              files: (dict[str, bytes | BinaryIO] |
                      dict[str, tuple[str, bytes | BinaryIO]] |
                      dict[str, tuple[str, bytes | BinaryIO, str]] |
                      dict[str, tuple[str, bytes | BinaryIO, str, dict[str, Any]]]) = None,
              timeout: float = None,
              logger: Logger = None) -> Response:
    """
    Issue a *REST* request to the given *url*, and return the response received.

    Optional *Bearer Authorization* data may be provided in *auth*, with the structure:
    {
      "scheme": <authorization-scheme> - currently, only "bearer" is accepted
      "url": <url>                     - the URL for obtaining the JWT token
      "<claim_i...n>": <jwt-claim>     - optional claims
    }

    To send multipart-encoded files, the optional *files* parameter is used, formatted as
    a *dict* holding pairs of *name* and:
      - a *file-content*, or
      - a *tuple* holding *file-name, file-content*, or
      - a *tuple* holding *file-name, file-content, content-type*, or
      - a *tuple* holding *file-name, file-content, content-type, custom-headers*
    These parameter elements are:
      - *file-name*: the name of the file
      _ *file-content*: the file contents, or a pointer obtained from *Path.open()* or *BytesIO*
      - *content-type*: the mimetype of the file
      - *custom-headers*: a *dict* containing additional headers for the file
     The *files* parameter is considered if *method* is *POST*, and disregarded otherwise.

    :param errors: incidental error messages
    :param method: the REST method to use (DELETE, GET, HEAD, PATCH, POST or PUT)
    :param url: the destination URL
    :param headers: optional headers
    :param params: optional parameters to send in the query string of the request
    :param data: optionaL data to send in the body of the request
    :param json: optional JSON to send in the body of the request
    :param files: optionally, one or more files to send
    :param timeout: request timeout, in seconds (defaults to 'None')
    :param logger: optional logger to log the operation with
    :return: the response to the REST operation, or 'None' if an error ocurred
    """
    # initialize the return variable
    result: Response | None = None

    if logger:
        logger.debug(msg=f"{method} '{url}'")

    # adjust the 'files' parameter, converting 'bytes' to a file pointer
    x_files: Any = None
    if method == HttpMethod.POST and isinstance(files, dict):
        # SANITY-CHECK: use a copy of 'files'
        x_files: dict[str, Any] = files.copy()
        for key, value in files.items():
            if isinstance(value, bytes):
                # 'files' is type 'dict[str, bytes]'
                x_files[key] = BytesIO(value)
                x_files[key].seek(0)
            elif isinstance(value, tuple) and isinstance(value[1], bytes):
                # 'value' is type 'tuple[str, bytes, ...]'
                x_files[key] = list(value)
                x_files[key][1] = BytesIO(value[1])
                x_files[key][1].seek(0)
                x_files[key] = tuple(x_files[key])

    # send the request
    err_msg: str | None = None
    try:
        result = requests.request(method=method.name,
                                  url=url,
                                  headers=headers,
                                  params=params,
                                  data=data,
                                  json=json,
                                  files=x_files,
                                  timeout=timeout)

        # was the request successful ?
        if result.status_code < 200 or result.status_code >= 300:
            # no, report the problem
            err_msg = (f"{method} '{url}': failed, "
                       f"status {result.status_code}, reason '{result.reason}'")
        elif logger:
            # yes, log the result
            logger.debug(msg=(f"{method} '{url}': "
                              f"status {result.status_code} "
                              f"({http_status_name(result.status_code)})"))
    except Exception as e:
        # the operation raised an exception
        err_msg = exc_format(exc=e,
                             exc_info=sys.exc_info())
        err_msg = f"{method} '{url}': error, '{err_msg}'"

    # is there an error message ?
    if err_msg:
        # yes, log and save it
        if logger:
            logger.error(msg=err_msg)
        if isinstance(errors, list):
            errors.append(err_msg)

    return result

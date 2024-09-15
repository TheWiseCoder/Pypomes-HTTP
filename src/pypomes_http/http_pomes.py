import contextlib
import requests
import sys
from flask import Request
from logging import Logger
from io import BytesIO
from pypomes_core import APP_PREFIX, env_get_float, exc_format
from pypomes_jwt import jwt_get_token, jwt_request_token
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
                            lang: Literal["en", "pt"] = "en") -> str:
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
        - parameters in the URL's query string
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
            result = request.get_json().get(param)

    return result


def http_get_parameters(request: Request) -> dict[str, Any]:
    """
    Obtain the *request*'s input parameters.

    The following are cumulatively attempted, in sequence:
        - key/value pairs in a *JSON* structure in the request's body
        - parameters in the URL's query string
        - elements in a HTML form

    :param request: the Request object
    :return: dict containing the input parameters (empty, if no input data exists)
    """
    # initialize the return variable
    result: dict[str, Any] = {}

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
                headers: dict[str, str] = None,
                params: dict[str, Any]  = None,
                data: dict[str, Any] = None,
                json: dict[str, Any] = None,
                auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to HTTP_DELETE_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the DELETE operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method="DELETE",
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     auth=auth,
                     timeout=timeout,
                     logger=logger)


def http_get(errors: list[str] | None,
             url: str,
             headers: dict[str, str] = None,
             params: dict[str, Any]  = None,
             data: dict[str, Any] = None,
             json: dict[str, Any] = None,
             auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to HTTP_GET_TIMEOUT - use None to omit)
    :param logger: optional logger
    :return: the response to the GET operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method="GET",
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     auth=auth,
                     timeout=timeout,
                     logger=logger)


def http_head(errors: list[str] | None,
              url: str,
              headers: dict[str, str] = None,
              params: dict[str, Any]  = None,
              data: dict[str, Any] = None,
              json: dict[str, Any] = None,
              auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to HTTP_HEAD_TIMEOUT - use None to omit)
    :param logger: optional logger
    :return: the response to the HEAD operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method="HEAD",
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     auth=auth,
                     timeout=timeout,
                     logger=logger)


def http_patch(errors: list[str] | None,
               url: str,
               headers: dict[str, str] = None,
               params: dict[str, Any]  = None,
               data: dict[str, Any] = None,
               json: dict[str, Any] = None,
               auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to HTTP_PATCH_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the PATCH operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method="PATCH",
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     auth=auth,
                     timeout=timeout,
                     logger=logger)


def http_post(errors: list[str] | None,
              url: str,
              headers: dict[str, str] = None,
              params: dict[str, Any]  = None,
              data: dict[str, Any] = None,
              json: dict[str, Any] = None,
              files: dict[str, bytes | BinaryIO] |
                     dict[str, tuple[str, bytes | BinaryIO]] |
                     dict[str, tuple[str, bytes | BinaryIO, str]] |
                     dict[str, tuple[str, bytes | BinaryIO, str, dict[str, Any]]] = None,
              auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to HTTP_POST_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the POST operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method="POST",
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     files=files,
                     auth=auth,
                     timeout=timeout,
                     logger=logger)


def http_put(errors: list[str] | None,
             url: str,
             headers: dict[str, str] = None,
             params: dict[str, Any]  = None,
             data: dict[str, Any] = None,
             json: dict[str, Any] = None,
             auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to HTTP_PUT_TIMEOUT - use None to omit)
    :param logger: optional logger to log the operation with
    :return: the response to the PUT operation, or 'None' if an error ocurred
    """
    return http_rest(errors=errors,
                     method="PUT",
                     url=url,
                     headers=headers,
                     params=params,
                     data=data,
                     json=json,
                     auth=auth,
                     timeout=timeout,
                     logger=logger)


def http_rest(errors: list[str],
              method: Literal["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"],
              url: str,
              headers: dict[str, str] = None,
              params: dict[str, Any]  = None,
              data: dict[str, Any] = None,
              json: dict[str, Any] = None,
              files: dict[str, bytes | BinaryIO] |
                     dict[str, tuple[str, bytes | BinaryIO]] |
                     dict[str, tuple[str, bytes | BinaryIO, str]] |
                     dict[str, tuple[str, bytes | BinaryIO, str, dict[str, Any]]] = None,
              auth: dict[str, Any] = None,
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
    :param auth: optional authentication scheme to use
    :param timeout: request timeout, in seconds (defaults to 'None')
    :param logger: optional logger to log the operation with
    :return: the response to the REST operation, or 'None' if an error ocurred
    """
    # initialize the return variable
    result: Response | None = None

    # clone the headers object
    op_headers: dict[str, str] = headers.copy() if headers else None

    # initialize the error message
    err_msg: str | None = None

    if logger:
        logger.debug(msg=f"{method} '{url}'")

    # initialize the local errors list
    op_errors: list[str] = []

    # satisfy authorization requirements
    jwt_data: dict[str, Any] = dict(auth or {})
    if jwt_data:
        # is it a 'Bearer Authentication' ?
        if jwt_data.pop("scheme", None) == "bearer":
            # yes, request the authentication token
            provider: str = jwt_data.pop("provider")
            # are there extra parameters in 'jwt_data' ?
            if jwt_data:
                # yes, obtain token data externally
                jwt_data = jwt_request_token(errors=op_errors,
                                             service_url=provider,
                                             claims=jwt_data,
                                             timeout=timeout,
                                             logger=logger)
            else:
                # no, obtain token data internally
                jwt_data = {"access_token": jwt_get_token(errors=op_errors,
                                                          service_url=provider,
                                                          logger=logger)}
            if not op_errors:
                op_headers = op_headers or {}
                op_headers["Authorization"] = f"Bearer {jwt_data.get('access_token')}"
            elif isinstance(errors, list):
                errors.extend(op_errors)
        else:
            # no, report the problem
            err_msg = f"Authentication scheme {auth.get('scheme')} not implemented"

    # proceed if no errors
    if not err_msg and not op_errors:
        # adjust the 'files' parameter, converting 'bytes' to a file pointer
        x_files: Any = None
        if method == "POST" and isinstance(files, dict):
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
        try:
            result = requests.request(method=method,
                                      url=url,
                                      headers=op_headers,
                                      params=params,
                                      data=data,
                                      json=json,
                                      files=x_files,
                                      timeout=timeout)
            # log the result
            if logger:
                logger.debug(msg=(f"{method} '{url}': "
                                  f"status {result.status_code} "
                                  f"({http_status_name(result.status_code)})"))
        except Exception as e:
            # the operation raised an exception
            exc_err: str = exc_format(exc=e,
                                      exc_info=sys.exc_info())
            err_msg = f"{method} '{url}': error, '{exc_err}'"

        # was the request successful ?
        if not result or \
           result.status_code < 200 or \
           result.status_code >= 300:
            # no, report the problem
            err_msg = (f"{method} '{url}': failed, "
                       f"status {result.status_code}, reason '{result.reason}'")

    # is there an error message ?
    if err_msg:
        # yes, log and/or save it
        if logger:
            logger.error(msg=err_msg)
        if isinstance(errors, list):
            errors.append(err_msg)

    return result

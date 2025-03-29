import contextlib
from base64 import b64encode
from flask import Request
from typing import Literal, Any

from .http_statuses import HttpStatus, _HTTP_STATUSES


def http_status_description(http_status: HttpStatus,
                            lang: Literal["en", "pt"] = "en") -> str:
    """
    Return the description of the HTTP status *status_code*.

    :param http_status: the HTTP status
    :param lang: optional language ('en' or 'pt' - defaults to 'en')
    :return: the corresponding HTTP status description, in the given language
    """
    item: dict = _HTTP_STATUSES.get(http_status)
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
        3. data elements in a HTML form

    :param request: the Request object
    :param sources: the sequence of sources to inspect (defaults to *['body', 'query', 'form']*)
    :param param: name of parameter to retrieve
    :return: the parameter's value, or *None* if not found
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
    :return: *dict* containing the input parameters (empty, if no input data exists)
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


def http_basic_auth_header(uname: str,
                           pwd: str,
                           header: dict[str, Any] = None) -> dict[str, Any]:
    """
    Add to *header* the HTTP Basic Authorization snippet.

    If *header* is not provided, a new *dict* is created.
    For convenience, the modified, or newly created, *dict* is returned.

    :param uname: the username to use
    :param pwd: the password to use
    :param header: the optional header to add the Basic Authorization to
    :return: header with Basic Authorization data
    """
    # initialize the return variable
    result: dict[str, Any] = header if isinstance(header, dict) else {}

    enc_bytes: bytes = b64encode(f"{uname}:{pwd}".encode())
    result["Authorization"] = f"Basic {enc_bytes.decode()}"

    return result


def http_bearer_auth_header(token: str | bytes,
                            header: dict[str, Any] = None) -> dict[str, Any]:
    """
    Add to *header* the HTTP Bearer Authorization snippet.

    If *header* is not provided, a new *dict* is created.
    For convenience, the modified, or newly created, *dict* is returned.

    :param token: the token to use
    :param header: the optional header to add the Bearer Authorization to
    :return: header with Basic Authorization data
    """
    # initialize the return variable
    result: dict[str, Any] = header if isinstance(header, dict) else {}

    if isinstance(token, bytes):
        token = token.decode()
    result["Authorization"] = f"Bearer {token}"

    return result

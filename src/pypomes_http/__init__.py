from .http_async import (
    HttpAsync,
)
from .http_pomes import (
    HTTP_DELETE_TIMEOUT, HTTP_GET_TIMEOUT, HTTP_HEAD_TIMEOUT,
    HTTP_PATCH_TIMEOUT, HTTP_POST_TIMEOUT, HTTP_PUT_TIMEOUT,
    MIMETYPE_BINARY, MIMETYPE_CSS, MIMETYPE_CSV, MIMETYPE_HTML, MIMETYPE_JAVASCRIPT,
    MIMETYPE_JSON, MIMETYPE_MULTIPART, MIMETYPE_PDF, MIMETYPE_PKCS7, MIMETYPE_SOAP,
    MIMETYPE_TEXT, MIMETYPE_URLENCODED, MIMETYPE_XML, MIMETYPE_ZIP,
    http_status_code, http_status_name, http_status_description,
    http_get_parameter, http_get_parameters,
    http_delete, http_get,  http_head, http_patch, http_post, http_put,
)

__all__ = [
    # http_async
    "HttpAsync",
    # http_pomes
    "HTTP_DELETE_TIMEOUT", "HTTP_GET_TIMEOUT", "HTTP_HEAD_TIMEOUT",
    "HTTP_PATCH_TIMEOUT", "HTTP_POST_TIMEOUT", "HTTP_PUT_TIMEOUT",
    "MIMETYPE_BINARY", "MIMETYPE_CSS", "MIMETYPE_CSV", "MIMETYPE_HTML", "MIMETYPE_JAVASCRIPT",
    "MIMETYPE_JSON", "MIMETYPE_MULTIPART", "MIMETYPE_PDF", "MIMETYPE_PKCS7", "MIMETYPE_SOAP",
    "MIMETYPE_TEXT", "MIMETYPE_URLENCODED", "MIMETYPE_XML", "MIMETYPE_ZIP",
    "http_status_code", "http_status_name", "http_status_description",
    "http_get_parameter", "http_get_parameters",
    "http_delete", "http_get", "http_head", "http_patch", "http_post", "http_put",
]

from importlib.metadata import version
__version__ = version("pypomes_http")
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())

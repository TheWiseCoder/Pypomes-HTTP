import base64
import json
import threading
from datetime import datetime
from logging import Logger
from pypomes_core import TIMEZONE_LOCAL
from typing import Literal
from requests import Response

from .http_pomes import _http_rest


class HttpAsync(threading.Thread):
    """
    Asynchronous invocation of a *REST* service.

    This invocation is done with *request* and the method specified in *job_method*.
    """

    def __init__(self, job_name: str, job_url: str,
                 job_method: Literal["GET", "POST", "PUT"],
                 callback: callable = None, report_content: bool = False,
                 headers: dict = None, params: dict = None, data: dict = None, json: dict = None,
                 auth: str = None, timeout: int = None, logger: Logger = None) -> None:
        """
        Initiate the asychronous invocation of the *REST* service.

        if a *callback* is specified, it will be sent the results of the job invocaton, in *JSON* format.
        This is the structure of the results sent:

        {
            "job_name": "<str>"             -- the name given for the job

            "start": "<iso-date>",          -- timestamp of invocation start (ISO format)

            "finish": "<iso-date>",         -- timestamp of invocation finish (ISO format)

            "errors": "<errors-reported>"   -- errors returned by the service, if applicable

            "response": "<bytes-in-BASE64>" -- Base64-wrapped contents of the response
        }

        :param job_name: name of the job being invoked
        :param job_url: the job's URL
        :param job_method: the REST method to use (GET, POST or PUT)
        :param callback: the function to call on job termination
        :param report_content: whether to report the response's content to callback
        :param headers: optional headers
        :param params: optional parameters
        :param auth: optional authentication scheme to use
        :param timeout: timeout, in seconds (defaults to None)
        :param logger: optional logger
        """
        threading.Thread.__init__(self)

        # instance attributes
        self.job_name: str = job_name
        self.job_url: str = job_url
        self.job_method = job_method
        self.callback = callback
        self.report_content = report_content
        self.headers = headers
        self.params = params
        self.data = data
        self.json = json
        self.auth = auth
        self.timeout = timeout
        self.logger: Logger = logger

        self.start_timestamp: str | None = None
        self.finish_timestamp: str | None = None

        if self.logger:
            self.logger.debug(f"Job '{job_name}' instantiated, with URL '{job_url}'")

    def run(self) -> None:
        """
        Invoke the *REST* service.
        """
        # initialize the errors list
        errors: list[str] = []

        if self.logger:
            self.logger.info(f"Job '{self.job_name}' started")

        # obtain the start timestamp
        self.start_timestamp = datetime.now(TIMEZONE_LOCAL).isoformat()

        # invoke the service
        response: Response = _http_rest(errors=errors,
                                        method=self.job_method,
                                        url=self.job_url,
                                        headers=self.headers,
                                        params=self.params,
                                        data=self.data,
                                        json=self.json,
                                        auth=self.auth,
                                        timeout=self.timeout,
                                        logger=self.logger)

        # obtain the finisg timestamp
        self.finish_timestamp = datetime.now(TIMEZONE_LOCAL).isoformat()

        if self.logger:
            self.logger.info(f"Job '{self.job_name}' finished")

        # has a callback been specified ?
        if self.callback:
            # yes, send it the results of the service invocation
            reply: dict = {
                "job_name": self.job_name,
                "start": self.start_timestamp,
                "finish": self.finish_timestamp
            }

            # any errors ?
            if len(errors) > 0:
                # yes, report the errors messages
                reply["errors"] = json.dumps(errors, ensure_ascii=False)
            elif self.report_content and \
                    response is not None and \
                    isinstance(response.content, bytes):
                reply["response"] = base64.b64encode(response.content).decode()

            # send message to recipient
            self.callback(reply)

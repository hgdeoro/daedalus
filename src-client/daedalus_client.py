# -*- coding: utf-8 -*-

##-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
##    daedalus - Centralized log server
##    Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
##
##    This file is part of daedalus.
##
##    daedalus is free software; you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation version 2.
##
##    daedalus is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License version 2 for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with daedalus; see the file LICENSE.txt.
##-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

import httplib
import logging
import os
import urllib
import json
import sys
import traceback

from hgdeoro.daedalus.utils import utc_str_timestamp


ERROR = 'ERROR'
WARN = 'WARN'
INFO = 'INFO'
DEBUG = 'DEBUG'


#===============================================================================
# Custom logger
#===============================================================================

class StdOutStdErrCustomLogger():

    def __init__(self, dest):
        self._dest = dest

    def _print(self, level, message):
        self._dest.write("> ")
        self._dest.write(level)
        self._dest.write(": ")
        self._dest.write(message)
        self._dest.write("\n")
        self._dest.flush()

    def debug(self, message):
        self._print("DEBUG", message)

    def info(self, message):
        self._print("INFO", message)

    def error(self, message):
        self._print("ERROR", message)

    def exception(self, message):
        exception_traceback = traceback.format_exc()
        self._print("ERROR", exception_traceback)
        self._print("ERROR", message)


class StdOutCustomLogger(StdOutStdErrCustomLogger):
    
    def __init__(self):
        StdOutStdErrCustomLogger.__init__(self, dest=sys.stdout)


class StdErrCustomLogger(StdOutStdErrCustomLogger):

    def __init__(self):
        StdOutStdErrCustomLogger.__init__(self, dest=sys.stderr)


def _createCustomLogger(custom_logger):
    if custom_logger is None or custom_logger == '':
        return logging.getLogger('DaedalusClient')
    if custom_logger == 'StdOutCustomLogger':
        return StdOutCustomLogger()
    if custom_logger == 'StdErrCustomLogger':
        return StdErrCustomLogger()
    # TODO: `custom_logger` could be a string referencing a class, like 'my.package.CustomLogger'
    raise(DaedalusException("Right now, only StdOutCustomLogger or StdErrCustomLogger are supported"))


#===============================================================================
# Daedalus client
#===============================================================================

class DaedalusException(Exception):
    pass


class DaedalusClient(object):
    """
    Creates an instance of a client to send messages to Daedalus.
    
    Parameters:
    - server_host: IP or hostname of the Daedalus server
    - port
    - default_message_host: `host` to use if no `host` is specified when calling `send_message()`.
    - default_message_application: `application` to use if no `application` is specified when calling `send_message()`.
    - log_client_errors: if True, the detected errors are logged.
    - raise_client_exceptions: if True, raises Exception when a error is detected.
    - custom_logger: custom logger to use instead of Python's `logging` framework.
    """
    def __init__(self, server_host="127.0.0.1", server_port=8085,
        default_message_host=None, default_message_application=None,
        log_client_errors=True, raise_client_exceptions=False,
        custom_logger=None):
        self.server_host = server_host
        self.server_port = server_port
        self.default_message_host = default_message_host
        self.default_message_application = default_message_application
        self.log_client_errors = log_client_errors
        self.raise_client_exceptions = raise_client_exceptions
        self._logger = _createCustomLogger(custom_logger)

    def send_message(self, message, severity=None, host=None, application=None):
        """
        Sends a message to the server using the current time.
        """
        try:
            self._send_message(message, severity, host, application)
        except DaedalusException:
            # If we get a DaedalusException, always re-raise them, since
            # they're raised only if 'self.raise_client_exceptions' is True
            raise
        except:
            # All other exceptions are ignored (are not re-raised,
            # even if 'self.raise_client_exceptions' is True
            # FIXME: should we re-raise this exception if 'self.raise_client_exceptions' is True?
            if self.log_client_errors:
                self._logger.exception("Couldn't send message to the server")

    def _send_message(self, message, severity, host, application):
        if severity is None:
            severity = 'INFO'
        if host is None:
            host = self.default_message_host
        if application is None:
            application = self.default_message_application

        timestamp = utc_str_timestamp()

        msg_dict = {
            'application': application,
            'host': host,
            'severity': severity,
            'timestamp': timestamp,
            'message': message,
        }
        json_message = json.dumps(msg_dict)
        params = urllib.urlencode({
            'payload': json_message,
        })
        conn = None
        try:
            conn = httplib.HTTPConnection(host=self.server_host, port=self.server_port)
            conn.request("POST", "/backend/save/", params, {})
            response = conn.getresponse()
            if response.status == 201:
                # response.status == 201
                try:
                    response_data = response.read()
                    response_dict = json.loads(response_data)
                    if response_dict['status'] == 'ok':
                        self._logger.debug("Log message sent OK.")
                        return
                except:
                    pass
                msg = "Even when http status was 201, something happened " \
                    "when trying to process the server response"
                if self.log_client_errors:
                    self._logger.error(msg)
                if self.raise_client_exceptions:
                    raise(DaedalusException(msg))
                return
            else:
                # response.status != 201
                # We should log a message, raise an exception, or both
                msg = "Invalid response from server. - status: {0} - reason: {1}".format(
                    response.status, response.reason)
                if self.log_client_errors:
                    # Try to read the content of the response
                    try:
                        response_data = response.read()
                    except:
                        self._logger.exception("Couldn't read the server response")
                        response_data = ''
                    self._logger.error(msg + "\n" + response_data)
                if self.raise_client_exceptions:
                    raise(DaedalusException(msg))
                else:
                    return
        finally:
            if conn is not None:
                try:
                    conn.close()
                except:
                    if self.log_client_errors:
                        self._logger.exception("Error detected when trying to close http connection")


if __name__ == '__main__':
    """
    Examples:
        $ sudo tail -f /var/log/syslog | env daedalus_app_name=syslog python -u daedalus_client.py
    """
    daedalus_host = os.environ.get('daedalus_host', 'localhost')
    daedalus_port = os.environ.get('daedalus_port', '8085')
    # FIXME: sanitize hostname, or at least check that it's valid
    daedalus_hostname = os.environ.get('daedalus_hostname', os.uname()[1])
    daedalus_app_name = os.environ.get('daedalus_app_name', 'os')
    client = DaedalusClient(daedalus_host, int(daedalus_port), daedalus_hostname,
        daedalus_app_name, log_client_errors=False, raise_client_exceptions=False)
    while True:
        try:
            for line in sys.stdin:
                msg = line.strip()
                client.send_message(msg, INFO)
        except KeyboardInterrupt:
            break

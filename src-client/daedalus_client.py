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

import calendar
import httplib
import json
import logging
import math
import optparse
import sys
import time
import traceback
import urllib


ERROR = 'ERROR'
WARN = 'WARN'
INFO = 'INFO'
DEBUG = 'DEBUG'


#===============================================================================
# This should be the same of `daedalus.utils.utc_now_from_epoch()`
#===============================================================================

def utc_now_from_epoch():
    """
    Returns a float timestamp representing the current time in seconds from epoch, as UTC.
    This is a UTC version of time.time()
    """
    current_time_from_epoch = time.time()
    utc_timetuple = time.gmtime(current_time_from_epoch)
    from_epoch = calendar.timegm(utc_timetuple) + math.modf(current_time_from_epoch)[0]
    return from_epoch


#===============================================================================
# This should be the same of `daedalus.utils.utc_str_timestamp()`
#===============================================================================

def utc_str_timestamp():
    """
    Returns a string representing the current time in UTC.
    The string represents a float: the seconds from EPOCH.
    """
    # First implementation. Worked OK, but found other method with better presission.
    #    utcnow = datetime.datetime.utcnow()
    #    timestamp = "{0}.{1:06}".format(calendar.timegm(utcnow.timetuple()), utcnow.microsecond)
    #    return timestamp

    # FIXME: change hardcoded '30' with the real precision of time.time()
    return "{0:0.30f}".format(utc_now_from_epoch())


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
    def __init__(self, server_host="127.0.0.1", server_port=64364,
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
            return self._send_message(message, severity, host, application)
        except:
            if self.log_client_errors:
                self._logger.exception("Couldn't send message to the server")
            if self.raise_client_exceptions:
                raise
            return False

    def _send_message(self, message, severity='INFO', host=None, application=None):
        timestamp = utc_str_timestamp()
        host = host or self.default_message_host or ''
        host = host.strip()
        application = application or self.default_message_application or ''
        application = application.strip()
        msg_dict = {
            'application': application,
            'host': host,
            'severity': severity,
            'timestamp': timestamp,
            'message': message,
        }
        params = urllib.urlencode(msg_dict)
        conn = None
        try:
            conn = httplib.HTTPConnection(host=self.server_host, port=self.server_port)
            conn.request("POST", "/backend/save/", params, {})
            response = conn.getresponse()
            if response.status == 201: # response.status == 201
                try:
                    response_data = response.read()
                    response_dict = json.loads(response_data)
                    if response_dict['status'] == 'ok':
                        self._logger.debug("Log message sent OK.")
                        return True
                    else:
                        raise(DaedalusException("Server returned status != ok. Status: {0}".format(
                            response_dict['status'])))
                except: # http, json, etc.
                    msg = "Even when http status was 201, something happened " \
                        "when trying to process the server response"
                    raise(DaedalusException(msg)) # @@@@@@@@@@
            else: # response.status != 201
                msg = "Invalid response from server. - status: {0} - reason: {1}".format(
                    response.status, response.reason)
                raise(DaedalusException(msg))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except:
                    if self.log_client_errors: # Don't rethrow this exception, it's not so important
                        self._logger.exception("Error detected when trying to close http connection")


#===============================================================================
# Main
#===============================================================================

description = """This is a CLI version of Daedalus client.
This utility allows you send messages to be stored on Daedalus.

This scripts returns with exit status = 0 if the message was sent.

By default, a severity of INFO is used.
"""


def _main(cli_args, stdin_file=sys.stdin, stdout_file=sys.stdout):
    parser = optparse.OptionParser(description=description)
    parser.add_option('-s', '--daedalus-server', default="localhost",
        help="Hostname or IP of Daedalus server",
        dest="daedalus_server")
    parser.add_option('-p', '--daedalus-port', default="64364", type="int",
        help="Port of Daedalus server",
        dest="daedalus_port")
    parser.add_option('-a', '--application',
        help="Name of the application that generated the message",
        dest="application")
    parser.add_option('-o', '--host',
        help="Name of the host that generated the message",
        dest="host")
    parser.add_option('-i', '--from-stdin',
        action="store_true", default=False,
        help="Read the message from STDIN",
        dest="from_stdin")
    parser.add_option('-m', '--message',
        help="Message to send",
        dest="message")
    parser.add_option('--show-client-exceptions',
        action="store_true", default=False,
        help="Show traceback of client exceptions",
        dest="show_client_exceptions")
    parser.add_option('--debug',
        action="store_true", default=False,
        help="Use DEBUG severity for the message",
        dest="severity_debug")
    parser.add_option('--info',
        action="store_true", default=False,
        help="Use INFO severity for the message",
        dest="severity_info")
    parser.add_option('--warn',
        action="store_true", default=False,
        help="Use WARN severity for the message",
        dest="severity_warn")
    parser.add_option('--error',
        action="store_true", default=False,
        help="Use ERROR severity for the message",
        dest="severity_error")

    (opts, args) = parser.parse_args(cli_args) #@UnusedVariable

    if not (opts.from_stdin or opts.message):
        stdout_file.write("ERROR: you must specify '--from-stdin' or '-m' or both")
        parser.print_help(file=stdout_file)
        return 1

    severity_sum = sum([1 for value in (opts.severity_error, opts.severity_warn, opts.severity_info,
        opts.severity_debug, ) if value])
    if severity_sum == 0 or opts.severity_info:
        # DEFAULT -> INFO
        severity = INFO
    elif severity_sum > 1:
        stdout_file.write("ERROR: you can only specify ONE severity, or use the default")
        parser.print_help(file=stdout_file)
        return 1
    else:
        if opts.severity_error:
            severity = ERROR
        elif opts.severity_warn:
            severity = WARN
        elif opts.severity_debug:
            severity = DEBUG
        else:
            severity = None

    assert severity is not None

    client = DaedalusClient(opts.daedalus_server, int(opts.daedalus_port),
        opts.host, opts.application,
        log_client_errors=False, raise_client_exceptions=opts.show_client_exceptions)

    # If an exceptino is raised, the exit status will be non-zero
    if opts.from_stdin and opts.message:
        sent_ok = client.send_message(opts.message + "\n" + stdin_file.read(), severity)
    elif opts.from_stdin:
        sent_ok = client.send_message(stdin_file.read(), severity)
    else:
        sent_ok = client.send_message(opts.message, severity)

    if sent_ok:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))

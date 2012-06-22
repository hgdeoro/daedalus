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
import time
import urllib
import json

logger = logging.getLogger(__name__)


class DaedalusException(Exception):
    pass


class DaedalusClient(object):

    def __init__(self, server_host="127.0.0.1", server_port=8000,
        default_message_host=None, default_message_application=None):
        self.server_host = server_host
        self.server_port = server_port
        self.default_message_host = default_message_host
        self.default_message_application = default_message_application

    def send_message(self, message, severity=None, host=None, application=None, timestamp=None):
        if timestamp is None:
            timestamp = "{0:0.25f}".format(time.time())
        if severity is None:
            severity = 'INFO'
        if host is None:
            host = self.default_message_host
        if application is None:
            application = self.default_message_application
        # respose = self.client.post('/save/', {'payload': json_message})
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
            conn.request("POST", "/save/", params, {})
            response = conn.getresponse()
            # print response.status, response.reason
            if response.status == 201:
                pass
            else:
                # FIXME: log this error
                # FIXME: raise better exception
                msg = "Invalid response from server. - status: {0} - reason: {1}".format(
                    response.status, response.reason)
                try:
                    response_data = response.read()
                except:
                    # FIXME: maybe we should log this error too
                    response_data = ''
                logger.error(msg + "\n" + response_data)
                raise(DaedalusException(msg))
            response_data = response.read()
            response_dict = json.loads(response_data)
            if not 'status' in response_dict or response_dict['status'] != 'ok':
                # FIXME: log this error
                # FIXME: raise better exception
                raise(DaedalusException("Invalid response from server"))
        finally:
            if conn is not None:
                try:
                    conn.close()
                except:
                    logger.exception("Error detected when trying to close http connection")

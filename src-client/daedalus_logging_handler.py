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

import logging
import pprint

from daedalus_client import DaedalusClient, ERROR, WARN, INFO, DEBUG

PYTHON2DAEDALUS = {
    'CRITICAL': ERROR,
    'ERROR': ERROR,
    'WARNING': WARN,
    'INFO': INFO,
    'DEBUG': DEBUG,
}


def print_record(record):
    print ">>>>", pprint.pformat(record)
    for att in [att for att in dir(record) if not att.startswith('_')]:
        try:
            print "    >> +", att, ":", getattr(record, att)
        except:
            pass


class CustomHandler(logging.Handler):

    def __init__(self, daedalus_host, daedalus_port, host, application, daedalus_debug=False, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self._daedalus_host = daedalus_host
        self._daedalus_port = int(daedalus_port)
        self._host = host
        self._application = application
        self._debug = daedalus_debug
        self._daedalus_client = DaedalusClient(
            self._daedalus_host,
            self._daedalus_port,
            default_message_host=self._host,
            default_message_application=self._application,
            log_client_errors=self._debug,
            custom_logger='StdOutCustomLogger',
        )

    def emit(self, record):
        if self._debug:
            print_record(record)
        self._daedalus_client.send_message(
            record.getMessage(),
            PYTHON2DAEDALUS[record.levelname],
            self._host,
            self._application
        )

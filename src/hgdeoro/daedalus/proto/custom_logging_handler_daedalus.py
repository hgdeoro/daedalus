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

from daedalus_client import DaedalusClient, ERROR, WARN, INFO, DEBUG

PYTHON2DAEDALUS = {
    'CRITICAL': ERROR,
    'ERROR': ERROR,
    'WARNING': WARN,
    'INFO': INFO,
    'DEBUG': DEBUG,
}


class CustomHandler(logging.Handler):

    def __init__(self, daedalus_host, daedalus_port, host, application, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self._daedalus_host = daedalus_host
        self._daedalus_port = daedalus_port
        self._host = host
        self._application = application
        self._daedalus_client = DaedalusClient(
            self._daedalus_host,
            self._daedalus_port,
            default_message_host=self._host,
            default_message_application=self._application,
            log_client_errors=False,
        )

    def emit(self, record):
        self._daedalus_client.send_message(
            record.message,
            PYTHON2DAEDALUS[record.levelname],
            self._host,
            self._application
        )

if __name__ == '__main__':
    logging.basicConfig()
    ch = CustomHandler("127.0.0.1", 8084, "acer", "sample-app")
    ch.setLevel(logging.WARN)
    # ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)

    logging.debug("This is a DEBUG message.")
    logging.info("This is a INFO message.")
    logging.warn("This is a WARN message.")
    logging.error("This is a ERROR message.")
    logging.critical("This is a CRITICAL message.")

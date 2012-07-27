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


class CustomHandler(logging.Handler):

    def __init__(self, daedalus_host, daedalus_port, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self.daedalus_host = daedalus_host
        self.daedalus_port = daedalus_port

    def emit(self, record):
        assert isinstance(record, logging.LogRecord)
        print ">>>", pprint.pformat(record)
        for att in [att for att in dir(record) if not att.startswith('_')]:
            try:
                print "    +", att, ":", getattr(record, att)
            except:
                pass

if __name__ == '__main__':
    logging.basicConfig()
    ch = CustomHandler("127.0.0.1", 8084)
    ch.setLevel(logging.WARN)
    # ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)

    logging.debug("This is a DEBUG message.")
    logging.info("This is a INFO message.")
    logging.warn("This is a WARN message.")
    logging.error("This is a ERROR message.")

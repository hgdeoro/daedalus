# -*- coding: utf-8 -*-

##-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
##    lolog - Centralized log server
##    Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
##
##    This file is part of lolog.
##
##    lolog is free software; you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation version 2.
##
##    lolog is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License version 2 for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with lolog; see the file LICENSE.txt.
##-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

import logging

from pycassa.columnfamily import ColumnFamily

from hgdeoro.lolog.proto import simple_client
from hgdeoro.lolog.proto.simple_client import CF_LOGS


def query(pool):
    logging.info("-" * 120) # ------------------------------
    logging.info("-" * 120) # ------------------------------
    cf_logs = ColumnFamily(pool, CF_LOGS)
    for obj in cf_logs.get_range(): #@UnusedVariable
        print "Key: {0}".format(obj[0])
        # print dir(obj[1])
        for k, v in obj[1].iteritems():
            print "    {0} -> {1}".format(k, v)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    pool = simple_client.get_connection()
    query(pool)

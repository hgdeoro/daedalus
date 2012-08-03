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

from pycassa.columnfamily import ColumnFamily
from pycassa.cassandra.c10.ttypes import NotFoundException

from daedalus.proto import simple_client
from daedalus.proto.simple_client import CF_LOGS, CF_LOGS_BY_APP,\
    CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY
from daedalus.proto.random_log_generator import EXAMPLE_APPS, EXAMPLE_HOSTS
from daedalus.utils import ymd_from_epoch


def query(pool):
    cf_logs = ColumnFamily(pool, CF_LOGS)
    row_key = ymd_from_epoch()
    try:
        cf_logs.get(row_key, column_count=0)
    except NotFoundException:
        # FIXME: this is extremely inefficient!
        row_key = cf_logs.get_range().next()[0]

    logging.info("-" * 120) # ------------------------------
    logging.info("Querying for key %s", row_key)
    logging.info("-" * 120) # ------------------------------
    count = 20
    for k, v in cf_logs.get(row_key, column_reversed=True).iteritems(): #@UnusedVariable
        logging.info(v)
        count -= 1
        if count == 0:
            break
    del cf_logs

    logging.info("-" * 120) # ------------------------------
    cf_logs_by_app = ColumnFamily(pool, CF_LOGS_BY_APP)
    row_key = EXAMPLE_APPS[0]
    logging.info("Querying for key %s", row_key)
    logging.info("-" * 120) # ------------------------------
    count = 20
    for k, v in cf_logs_by_app.get(row_key, column_reversed=True).iteritems(): #@UnusedVariable
        logging.info(v)
        count -= 1
        if count == 0:
            break
    del cf_logs_by_app

    logging.info("-" * 120) # ------------------------------
    cf_logs_by_host = ColumnFamily(pool, CF_LOGS_BY_HOST)
    row_key = EXAMPLE_HOSTS[0]
    logging.info("Querying for key %s", row_key)
    logging.info("-" * 120) # ------------------------------
    count = 20
    for k, v in cf_logs_by_host.get(row_key, column_reversed=True).iteritems(): #@UnusedVariable
        logging.info(v)
        count -= 1
        if count == 0:
            break
    del cf_logs_by_host

    logging.info("-" * 120) # ------------------------------
    cf_logs_by_severity = ColumnFamily(pool, CF_LOGS_BY_SEVERITY)
    row_key = 'WARN'
    logging.info("Querying for key %s", row_key)
    logging.info("-" * 120) # ------------------------------
    count = 20
    for k, v in cf_logs_by_severity.get(row_key, column_reversed=True).iteritems(): #@UnusedVariable
        logging.info(v)
        count -= 1
        if count == 0:
            break
    del cf_logs_by_severity


def main():
    pool = simple_client.get_connection()
    query(pool)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

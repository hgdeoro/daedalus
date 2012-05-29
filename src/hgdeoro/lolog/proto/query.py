# -*- coding: utf-8 -*-

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import logging
import uuid

from pycassa.columnfamily import ColumnFamily

from hgdeoro.lolog.proto import simple_client
from hgdeoro.lolog.proto.simple_client import CF_LOGS, CF_LOGS_BY_APP,\
    CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY
from hgdeoro.lolog.proto.random_log_generator import EXAMPLE_APPS, EXAMPLE_HOSTS


def query(pool):
    logging.info("-" * 120) # ------------------------------
    cf_logs = ColumnFamily(pool, CF_LOGS)
    row_key = (uuid.uuid1().time / 10 ** 7) / (60 * 60 * 24)
    logging.info("Querying for key %s", str(row_key))
    logging.info("-" * 120) # ------------------------------
    count = 20
    for k, v in cf_logs.get(str(row_key)).iteritems(): #@UnusedVariable
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
    for k, v in cf_logs_by_app.get(row_key).iteritems(): #@UnusedVariable
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
    for k, v in cf_logs_by_host.get(row_key).iteritems(): #@UnusedVariable
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
    for k, v in cf_logs_by_severity.get(row_key).iteritems(): #@UnusedVariable
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

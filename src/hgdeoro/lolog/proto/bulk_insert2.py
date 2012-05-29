# -*- coding: utf-8 -*-

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import logging
import random
import time
import uuid

from pycassa.columnfamily import ColumnFamily

from hgdeoro.lolog.proto import simple_client
from hgdeoro.lolog.proto.simple_client import CF_LOGS, CF_LOGS_BY_APP,\
    CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY
from hgdeoro.lolog.proto.random_log_generator import log_generator


def mass_insert(pool):
    cf_logs = ColumnFamily(pool, CF_LOGS)
    cf_logs_by_app = ColumnFamily(pool, CF_LOGS_BY_APP)
    cf_logs_by_host = ColumnFamily(pool, CF_LOGS_BY_HOST)
    cf_logs_by_severity = ColumnFamily(pool, CF_LOGS_BY_SEVERITY)
    rnd_inst = random.Random()
    rnd_inst.seed(1)
    start = time.time()
    count = 0
    try:
        for item in log_generator(1):
            msg = item[0]
            app = item[1]
            host = item[2]
            severity = item[3]

            # http://pycassa.github.com/pycassa/assorted/time_uuid.html
            # http://www.slideshare.net/jeremiahdjordan/pycon-2012-apache-cassandra
            # http://www.slideshare.net/rbranson/how-do-i-cassandra @ slide 80
            # https://github.com/pycassa/pycassa/issues/135

            # Save on <CF> CF_LOGS
            event_uuid = uuid.uuid1()
            row_key = (event_uuid.time / 10 ** 7) / (60 * 60 * 24)
            cf_logs.insert(str(row_key), {
                event_uuid: msg,
            })

            # Save on <CF> CF_LOGS_BY_APP
            cf_logs_by_app.insert(app, {
                event_uuid: msg,
            })

            # Save on <CF> CF_LOGS_BY_HOST
            cf_logs_by_host.insert(host, {
                event_uuid: msg,
            })

            # Save on <CF> CF_LOGS_BY_SEVERITY
            cf_logs_by_severity.insert(severity, {
                event_uuid: msg,
            })

            count += 4
            if count % 400 == 0:
                avg = float(count) / (time.time() - start)
                logging.info("Inserted %d columns, %f insert/sec", count, avg)
    except KeyboardInterrupt:
        logging.info("Stopping...")
    end = time.time()
    avg = float(count) / (end - start)
    logging.info("%d columns inserted. Avg: %f insert/sec", count, avg)


def main():
    pool = simple_client.get_connection()
    mass_insert(pool)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

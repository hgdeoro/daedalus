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
from hgdeoro.lolog.proto.simple_client import CF_LOGS
from hgdeoro.lolog.proto.random_log_generator import log_generator


def mass_insert(pool):
    cf_logs = ColumnFamily(pool, CF_LOGS)
    rnd_inst = random.Random()
    rnd_inst.seed(1)
    start = time.time()
    count = 0
    try:
        for item in log_generator(1):
            msg = item[0]
            app = item[1]

            # http://pycassa.github.com/pycassa/assorted/time_uuid.html
            # http://www.slideshare.net/jeremiahdjordan/pycon-2012-apache-cassandra
            # http://www.slideshare.net/rbranson/how-do-i-cassandra @ slide 80
            # https://github.com/pycassa/pycassa/issues/135
            cf_logs.insert(app, {
                uuid.uuid1(): msg,
            })
            count += 1
            if count % 100 == 0:
                logging.info("Inserted %d columns", count)
    except KeyboardInterrupt:
        logging.info("Stopping...")
    end = time.time()
    avg = float(count) / (end - start)
    logging.info("Avg: %f insert/sec", avg)


def main():
    pool = simple_client.get_connection()
    mass_insert(pool)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

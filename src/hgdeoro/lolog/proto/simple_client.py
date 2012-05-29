# -*- coding: utf-8 -*-

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import logging
import os
import uuid

from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
from pycassa.types import TimeUUIDType

KEYSPACE = 'lolog'
CF_LOGS = 'Logs'
CF_LOGS_BY_APP = 'Logs_by_app'


def get_connection():
    """
    Creates a connection to Cassandra.

    Returs:
        pool
    """
    cassandra_host = os.environ.get('CASSANDRA_HOST', 'localhost')
    sys_mgr = SystemManager()
    try:
        sys_mgr.describe_ring(KEYSPACE)
    except:
        sys_mgr.create_keyspace(KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})

    pool = ConnectionPool(KEYSPACE, server_list=[cassandra_host])
    try:
        cf_logs = ColumnFamily(pool, CF_LOGS)
    except:
        sys_mgr.create_column_family(KEYSPACE, CF_LOGS, comparator_type=TimeUUIDType())
        cf_logs = ColumnFamily(pool, CF_LOGS)

    try:
        cf_logs_by_app = ColumnFamily(pool, CF_LOGS_BY_APP)
    except:
        sys_mgr.create_column_family(KEYSPACE, CF_LOGS_BY_APP, comparator_type=TimeUUIDType())
        cf_logs_by_app = ColumnFamily(pool, CF_LOGS_BY_APP)

    sys_mgr.close()
    cf_logs.get_count(str(uuid.uuid4()))
    cf_logs_by_app.get_count(str(uuid.uuid4()))

    return pool

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    get_connection()

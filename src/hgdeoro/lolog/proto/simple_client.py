# -*- coding: utf-8 -*-

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import logging
import os
import uuid

from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY

KEYSPACE = 'lolog'
CF_LOGS = 'Logs'


def get_connection():
    """
    Creates a connection to Cassandra.

    Returs:
        (pool, cf)
    """
    cassandra_host = os.environ.get('CASSANDRA_HOST', 'localhost')
    sys_mgr = SystemManager()
    try:
        sys_mgr.describe_ring(KEYSPACE)
    except:
        sys_mgr.create_keyspace(KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})

    pool = ConnectionPool(KEYSPACE, server_list=[cassandra_host])
    try:
        cf = ColumnFamily(pool, CF_LOGS)
    except:
        sys_mgr.create_column_family(KEYSPACE, CF_LOGS)
        cf = ColumnFamily(pool, CF_LOGS)

    sys_mgr.close()
    cf.get_count(str(uuid.uuid4()))

    return pool, cf

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    get_connection()

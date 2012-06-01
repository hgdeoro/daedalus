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
import os
import uuid

from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
from pycassa.types import TimeUUIDType

KEYSPACE = 'lolog'
CF_LOGS = 'Logs'
CF_LOGS_BY_APP = 'Logs_by_app'
CF_LOGS_BY_HOST = 'Logs_by_host'
CF_LOGS_BY_SEVERITY = 'Logs_by_severity'


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
    for cf_name in [CF_LOGS, CF_LOGS_BY_APP, CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY]:
        try:
            cf = ColumnFamily(pool, cf_name)
        except:
            sys_mgr.create_column_family(KEYSPACE, cf_name, comparator_type=TimeUUIDType())
            cf = ColumnFamily(pool, cf_name)
            cf.get_count(str(uuid.uuid4()))

    sys_mgr.close()

    return pool

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    get_connection()

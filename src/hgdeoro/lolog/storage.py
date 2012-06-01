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

import json
import logging
import uuid

from django.conf import settings

from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
from pycassa.types import TimeUUIDType

from hgdeoro.lolog.utils import ymd_from_uuid1

logger = logging.getLogger(__name__)

KEYSPACE = 'lolog'
CF_LOGS = 'Logs'
CF_LOGS_BY_APP = 'Logs_by_app'
CF_LOGS_BY_HOST = 'Logs_by_host'
CF_LOGS_BY_SEVERITY = 'Logs_by_severity'


def _get_connection():
    """
    Creates a connection to Cassandra.

    Returs:
        pool
    """
    sys_mgr = SystemManager()
    try:
        sys_mgr.describe_ring(KEYSPACE)
    except:
        sys_mgr.create_keyspace(KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})

    pool = ConnectionPool(KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
    for cf_name in [CF_LOGS, CF_LOGS_BY_APP, CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY]:
        try:
            cf = ColumnFamily(pool, cf_name)
        except:
            sys_mgr.create_column_family(KEYSPACE, cf_name, comparator_type=TimeUUIDType())
            cf = ColumnFamily(pool, cf_name)
            cf.get_count(str(uuid.uuid4()))

    sys_mgr.close()

    return pool


def save_log(message):
    pool = _get_connection()
    cf_logs = ColumnFamily(pool, CF_LOGS)
    cf_logs_by_app = ColumnFamily(pool, CF_LOGS_BY_APP)
    cf_logs_by_host = ColumnFamily(pool, CF_LOGS_BY_HOST)
    cf_logs_by_severity = ColumnFamily(pool, CF_LOGS_BY_SEVERITY)

    application = message['application']
    host = message['host']
    severity = message['severity']
    # timestamp = message['timestamp']
    
    json_message = json.dumps(message)

    # Save on <CF> CF_LOGS
    event_uuid = uuid.uuid1()
    row_key = ymd_from_uuid1(event_uuid)
    cf_logs.insert(str(row_key), {
        event_uuid: json_message,
    })

    # Save on <CF> CF_LOGS_BY_APP
    cf_logs_by_app.insert(application, {
        event_uuid: json_message,
    })

    # Save on <CF> CF_LOGS_BY_HOST
    cf_logs_by_host.insert(host, {
        event_uuid: json_message,
    })

    # Save on <CF> CF_LOGS_BY_SEVERITY
    cf_logs_by_severity.insert(severity, {
        event_uuid: json_message,
    })

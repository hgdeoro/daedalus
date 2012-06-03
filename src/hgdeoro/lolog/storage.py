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
import re
import uuid

from django.conf import settings
from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
from pycassa.types import TimeUUIDType

from hgdeoro.lolog.utils import ymd_from_uuid1

logger = logging.getLogger(__name__)

# TODO: this regex should be valid only for valid Cassandra row keys
APPLICATION_REGEX = re.compile(r'^[a-zA-Z0-9/-]+$')

CF_LOGS = 'Logs'
CF_LOGS_BY_APP = 'Logs_by_app'
CF_LOGS_BY_HOST = 'Logs_by_host'
CF_LOGS_BY_SEVERITY = 'Logs_by_severity'


def _check_severity(severity):
    assert severity in ('ERROR', 'WARN', 'INFO', 'DEBUG')


def _check_application(application):
    if not APPLICATION_REGEX.search(application):
        assert False, "Invalid identifier for application: '{0}'".format(application)


def _create_keyspace_and_cfs():
    """
    Creates the KEYSPACE and CF
    """
    sys_mgr = SystemManager()
    try:
        sys_mgr.describe_ring(settings.KEYSPACE)
    except:
        logger.info("_create_keyspace_and_cfs(): Creating keyspace %s", settings.KEYSPACE)
        sys_mgr.create_keyspace(settings.KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})

    pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
    for cf_name in [CF_LOGS, CF_LOGS_BY_APP, CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY]:
        try:
            cf = ColumnFamily(pool, cf_name)
        except:
            logger.info("_create_keyspace_and_cfs(): Creating column family %s", cf_name)
            sys_mgr.create_column_family(settings.KEYSPACE, cf_name, comparator_type=TimeUUIDType())
            cf = ColumnFamily(pool, cf_name)
            cf.get_count(str(uuid.uuid4()))

    sys_mgr.close()


def _get_connection():
    """
    Creates a connection to Cassandra.

    Returs:
        pool
    """
    pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
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

    _check_application(application)
    _check_severity(severity)

    json_message = json.dumps(message)

    # Save on <CF> CF_LOGS
    event_uuid = uuid.uuid1()
    row_key = ymd_from_uuid1(event_uuid)
    ret1 = cf_logs.insert(str(row_key), {
        event_uuid: json_message,
    })

    # Save on <CF> CF_LOGS_BY_APP
    ret2 = cf_logs_by_app.insert(application, {
        event_uuid: json_message,
    })

    # Save on <CF> CF_LOGS_BY_HOST
    ret3 = cf_logs_by_host.insert(host, {
        event_uuid: json_message,
    })

    # Save on <CF> CF_LOGS_BY_SEVERITY
    ret4 = cf_logs_by_severity.insert(severity, {
        event_uuid: json_message,
    })

    assert ret1 > 0
    assert ret2 > 0
    assert ret3 > 0
    assert ret4 > 0
    return ret1, ret2, ret3, ret4


def query():
    """
    Returns list of OrderedDict.

    Use:
        cassandra_result = query()
        result = []
        for _, columns in cassandra_result:
            for _, col in columns.iteritems():
                message = json.loads(col)
                result.append(message)
    """
    pool = _get_connection()
    cf_logs = ColumnFamily(pool, CF_LOGS)
    return cf_logs.get_range(column_reversed=True)


def query_by_severity(severity):
    """
    Returns OrderedDict.

    Use:
        cassandra_result = query_by_severity(severity)
        result = []
        for _, col in cassandra_result.iteritems():
            message = json.loads(col)
            result.append(message)
    """
    _check_severity(severity)
    pool = _get_connection()
    cf_logs = ColumnFamily(pool, CF_LOGS_BY_SEVERITY)
    return cf_logs.get(severity, column_reversed=True)


def query_by_application(application):
    """
    Returns OrderedDict.

    Use:
        cassandra_result = query_by_application(severity)
        result = []
        for _, col in cassandra_result.iteritems():
            message = json.loads(col)
            result.append(message)
    """
    _check_application(application)
    pool = _get_connection()
    cf_logs = ColumnFamily(pool, CF_LOGS_BY_APP)
    return cf_logs.get(application, column_reversed=True)


def list_applications():
    """
    Returns a list of valid applications.
    """
    pool = _get_connection()
    cf_logs = ColumnFamily(pool, CF_LOGS_BY_APP)
    return [item[0] for item in cf_logs.get_range(column_count=1)]

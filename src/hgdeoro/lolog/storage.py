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
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
from pycassa.types import TimeUUIDType
from pycassa.batch import Mutator
from pycassa.pool import AllServersUnavailable

from hgdeoro.lolog.utils import ymd_from_uuid1

logger = logging.getLogger(__name__)

# TODO: this regex should be valid only for valid Cassandra row keys
APPLICATION_REGEX = re.compile(r'^[a-zA-Z0-9/-]+$')

# TODO: this regex should be valid only for valid Cassandra row keys
HOST_REGEX = re.compile(r'^[a-zA-Z0-9-\.]+$')

CF_LOGS = 'Logs'
CF_LOGS_BY_APP = 'Logs_by_app'
CF_LOGS_BY_HOST = 'Logs_by_host'
CF_LOGS_BY_SEVERITY = 'Logs_by_severity'


def _json_cache(key, ttl, callback, *args, **kwargs):
    cached = cache.get(key)
    if cached is not None:
        return json.loads(cached)
    data = callback(*args, **kwargs)
    cache.set(key, json.dumps(data), ttl)
    return data


def _check_severity(severity):
    assert severity in ('ERROR', 'WARN', 'INFO', 'DEBUG')


def _check_application(application):
    if not APPLICATION_REGEX.search(application):
        assert False, "Invalid identifier for application: '{0}'".format(application)


def _check_host(host):
    if not HOST_REGEX.search(host):
        assert False, "Invalid identifier for host: '{0}'".format(host)


def _get_connection(retry=None, wait_between_retry=None):
    """
    Creates a connection to Cassandra.

    Returs:
        pool
    """
    num = 0
    if retry is None:
        retry = settings.CASSANDRA_CONNECT_RETRY_COUNT
    if wait_between_retry is None:
        wait_between_retry = settings.CASSANDRA_CONNECT_RETRY_WAIT
    while True:
        try:
            pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
            return pool
        except AllServersUnavailable:
            num += 1
            if num >= retry:
                logger.exception("Giving up after many retries....")
                raise
            logger.warn("AllServersUnavailable detected. Retrying (%d of %d)...", num, retry)
            time.sleep(wait_between_retry)


def get_service(*args, **kwargs):
    return StorageService(*args, **kwargs)


class StorageService(object):

    def __init__(self, cache_enabled=True):
        self.cache_enabled = cache_enabled

    def create_keyspace_and_cfs(self):
        """
        Creates the KEYSPACE and CF
        """
        sys_mgr = SystemManager()
        try:
            sys_mgr.describe_ring(settings.KEYSPACE)
        except:
            logger.info("create_keyspace_and_cfs(): Creating keyspace %s", settings.KEYSPACE)
            sys_mgr.create_keyspace(settings.KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})
    
        pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
        for cf_name in [CF_LOGS, CF_LOGS_BY_APP, CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY]:
            try:
                cf = ColumnFamily(pool, cf_name)
            except:
                logger.info("create_keyspace_and_cfs(): Creating column family %s", cf_name)
                sys_mgr.create_column_family(settings.KEYSPACE, cf_name, comparator_type=TimeUUIDType())
                cf = ColumnFamily(pool, cf_name)
                cf.get_count(str(uuid.uuid4()))
    
        sys_mgr.close()

    def save_log(self, message):
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
        event_uuid = uuid.uuid1()
    
        with Mutator(pool) as batch:
            # Save on <CF> CF_LOGS
            row_key = ymd_from_uuid1(event_uuid)
            batch.insert(
                cf_logs,
                str(row_key), {
                    event_uuid: json_message,
            })
    
            # Save on <CF> CF_LOGS_BY_APP
            batch.insert(
                cf_logs_by_app,
                application, {
                    event_uuid: json_message,
            })
    
            # Save on <CF> CF_LOGS_BY_HOST
            batch.insert(
                cf_logs_by_host,
                host, {
                    event_uuid: json_message,
            })
    
            # Save on <CF> CF_LOGS_BY_SEVERITY
            batch.insert(
                cf_logs_by_severity,
                severity, {
                    event_uuid: json_message,
            })
    
    def query(self):
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
    
    def query_by_severity(self, severity, from_col=None):
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
        if from_col is None:
            return cf_logs.get(severity, column_reversed=True)
        else:
            return cf_logs.get(severity, column_reversed=True, column_start=from_col)

    def query_by_application(self, application, from_col=None):
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
        if from_col is None:
            return cf_logs.get(application, column_reversed=True)
        else:
            return cf_logs.get(application, column_reversed=True, column_start=from_col)
    
    def query_by_host(self, host):
        """
        Returns OrderedDict.
    
        Use:
            cassandra_result = query_by_host(severity)
            result = []
            for _, col in cassandra_result.iteritems():
                message = json.loads(col)
                result.append(message)
        """
        _check_host(host)
        pool = _get_connection()
        cf_logs = ColumnFamily(pool, CF_LOGS_BY_HOST)
        return cf_logs.get(host, column_reversed=True)
    
    def list_applications(self):
        """
        Returns a list of valid applications.
        """
        def _callback():
            pool = _get_connection()
            cf_logs = ColumnFamily(pool, CF_LOGS_BY_APP)
            return [item[0] for item in cf_logs.get_range(column_count=1)]

        if self.cache_enabled:
            return _json_cache('lolog:application_list', settings.LOLOG_CACHE_APP_LIST, _callback)
        else:
            return _callback()

    def _get_severity_count(self, severity):
        def _callback():
            pool = _get_connection()
            cf_logs = ColumnFamily(pool, CF_LOGS_BY_SEVERITY)
            count = cf_logs.get_count(severity)
            return count

        if self.cache_enabled:
            cached_count = cache.get('lolog:severity_count:' + severity)
            if cached_count:
                return int(cached_count)
            count = _callback()
            cache.set('lolog:severity_count:' + severity, str(count),
                settings.LOLOG_CACHE_SEVERITY_COUNT)
            return count
        else:
            return _callback()

    def get_error_count(self):
        return self._get_severity_count('ERROR')
    
    def get_warn_count(self):
        return self._get_severity_count('WARN')
    
    def get_info_count(self):
        return self._get_severity_count('INFO')
    
    def get_debug_count(self):
        return self._get_severity_count('DEBUG')

    def get_status(self):
        status = {}
        _logger = logging.getLogger(__name__ + '.get_status')
        try:
            pool = _get_connection()
            pool.dispose()
            status['get_connection'] = "ok"
        except:
            status['get_connection'] = "error"
            _logger.exception("_get_connection() failed")

        try:
            status['get_error_count'] = self.get_error_count()
        except:
            status['get_error_count'] = "error"
            _logger.exception("get_error_count() failed")

        try:
            status['get_warn_count'] = self.get_warn_count()
        except:
            status['get_warn_count'] = "error"
            _logger.exception("get_warn_count() failed")

        try:
            status['get_info_count'] = self.get_info_count()
        except:
            status['get_info_count'] = "error"
            _logger.exception("get_info_count() failed")

        try:
            status['get_debug_count'] = self.get_debug_count()
        except:
            status['get_debug_count'] = "error"
            _logger.exception("get_debug_count() failed")

        try:
            self.query()
            status['query'] = "ok"
        except:
            status['query'] = "error"
            _logger.exception("query() failed")

        try:
            apps = self.list_applications()
            status['list_applications'] = ", ".join(apps)
            for app in apps:
                try:
                    status['query_by_application_' + app] = len(self.query_by_application(app).keys())
                except:
                    status['query_by_application_' + app] = "error"
                    _logger.exception("query_by_application() failed")
        except:
            status['list_applications'] = "error"
            _logger.exception("list_applications() failed")

        sys_mgr = SystemManager()
        try:
            sys_mgr.describe_ring(settings.KEYSPACE)
            status['SystemManager.describe_ring(%s)' % settings.KEYSPACE] = 'ok'
        except:
            status['SystemManager.describe_ring(%s)' % settings.KEYSPACE] = 'error'
            _logger.exception("SystemManager.describe_ring() failed")

        return status

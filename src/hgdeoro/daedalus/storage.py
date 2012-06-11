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

import contextlib
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
from pycassa.util import convert_time_to_uuid

from hgdeoro.daedalus.utils import ymd_from_uuid1

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
            pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS,
                timeout=settings.CASSANDRA_CONNECTION_POOL_TIMEOUT)
            return pool
        except AllServersUnavailable:
            num += 1
            if num >= retry:
                logger.exception("Giving up after many retries....")
                raise
            logger.warn("AllServersUnavailable detected. Retrying (%d of %d)...", num, retry)
            time.sleep(wait_between_retry)


#@contextlib.contextmanager
#def _get_connection_cm(*args, **kwargs):
#    """
#    Use:
#        with _get_connection_cm() as pool:
#            pass
#    """
#    pool = None
#    try:
#        pool = _get_connection(*args, **kwargs)
#        yield pool
#    finally:
#        if pool is not None:
#            pool.dispose()


def get_service(*args, **kwargs):
    return StorageService(*args, **kwargs)


@contextlib.contextmanager
def get_service_cm(*args, **kwargs):
    """
    Generates context manager for a service instance.

    Use:
        with get_service_cm() as service:
            pass
    """
    service = StorageService(*args, **kwargs)
    try:
        yield service
    finally:
        service.close()


class StorageService(object):
    # FIXME: ensure close() is called on every instance created elsewhere

    def __init__(self, cache_enabled=True):
        self._cache_enabled = cache_enabled
        self._pool = None
        self._cf_logs = None
        self._cf_logs_by_app = None
        self._cf_logs_by_host = None
        self._cf_logs_by_severity = None

    def _get_pool(self):
        if self._pool is None:
            self._pool = _get_connection()
        return self._pool

    def _get_cf_logs(self):
        if self._cf_logs is None:
            self._cf_logs = ColumnFamily(self._get_pool(), CF_LOGS)
        return self._cf_logs

    def _get_cf_logs_by_app(self):
        if self._cf_logs_by_app is None:
            self._cf_logs_by_app = ColumnFamily(self._get_pool(), CF_LOGS_BY_APP)
        return self._cf_logs_by_app

    def _get_cf_logs_by_host(self):
        if self._cf_logs_by_host is None:
            self._cf_logs_by_host = ColumnFamily(self._get_pool(), CF_LOGS_BY_HOST)
        return self._cf_logs_by_host

    def _get_cf_logs_by_severity(self):
        if self._cf_logs_by_severity is None:
            self._cf_logs_by_severity = ColumnFamily(self._get_pool(), CF_LOGS_BY_SEVERITY)
        return self._cf_logs_by_severity

    def close(self):
        if self._pool is not None:
            self._pool.dispose()
            self._pool = None

    def create_keyspace_and_cfs(self):
        """
        Creates the KEYSPACE and CF
        """
        try:
            sys_mgr = SystemManager()
            try:
                sys_mgr.describe_ring(settings.KEYSPACE)
            except:
                logger.info("create_keyspace_and_cfs(): Creating keyspace %s", settings.KEYSPACE)
                sys_mgr.create_keyspace(settings.KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})
    
            try:
                pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
                for cf_name in [CF_LOGS, CF_LOGS_BY_APP, CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY]:
                    try:
                        cf = ColumnFamily(pool, cf_name)
                    except:
                        logger.info("create_keyspace_and_cfs(): Creating column family %s", cf_name)
                        sys_mgr.create_column_family(settings.KEYSPACE, cf_name, comparator_type=TimeUUIDType())
                        cf = ColumnFamily(pool, cf_name)
                        cf.get_count(str(uuid.uuid4()))
            finally:
                pool.dispose()
        finally:
            sys_mgr.close()

    def save_log(self, message):
        pool = self._get_pool()

        application = message['application']
        host = message['host']
        severity = message['severity']
        timestamp = message['timestamp']

        _check_application(application)
        _check_severity(severity)

        event_uuid = convert_time_to_uuid(float(timestamp), randomize=True)
        message['_uuid'] = event_uuid.get_hex()
        json_message = json.dumps(message)

        with Mutator(pool) as batch:
            # Save on <CF> CF_LOGS
            row_key = ymd_from_uuid1(event_uuid)
            batch.insert(
                self._get_cf_logs(),
                str(row_key), {
                    event_uuid: json_message,
            })

            # Save on <CF> CF_LOGS_BY_APP
            batch.insert(
                self._get_cf_logs_by_app(),
                application, {
                    event_uuid: json_message,
            })

            # Save on <CF> CF_LOGS_BY_HOST
            batch.insert(
                self._get_cf_logs_by_host(),
                host, {
                    event_uuid: json_message,
            })

            # Save on <CF> CF_LOGS_BY_SEVERITY
            batch.insert(
                self._get_cf_logs_by_severity(),
                severity, {
                    event_uuid: json_message,
            })

    def query(self):
        """
        Returns list of dicts.
        """
        result = []
        cassandra_result = self._get_cf_logs().get_range(column_reversed=True)
        for _, columns in cassandra_result:
            for _, col_val in columns.iteritems():
                result.append(json.loads(col_val))
        return result

    def get_by_id(self, message_id):
        # FIXME: add documentation
        # FIXME: add tests
        # FIXME: return None if doesn't exists
        msg_uuid = uuid.UUID(hex=message_id)
        row_key = ymd_from_uuid1(msg_uuid)
        json_str = self._get_cf_logs().get(row_key, columns=[msg_uuid])[msg_uuid]
        return json.loads(json_str)

    def query_by_severity(self, severity, from_col=None):
        """
        Returns list of dicts.
        """
        _check_severity(severity)
        if from_col is None:
            cass_result = self._get_cf_logs_by_severity().get(severity, column_reversed=True)
        else:
            cass_result = self._get_cf_logs_by_severity().get(severity, column_reversed=True, column_start=from_col)
        return [json.loads(col_val) for _, col_val in cass_result.iteritems()]

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
        if from_col is None:
            cass_result = self._get_cf_logs_by_app().get(application, column_reversed=True)
        else:
            cass_result = self._get_cf_logs_by_app().get(application, column_reversed=True, column_start=from_col)
        return [json.loads(col_val) for _, col_val in cass_result.iteritems()]
    
    def query_by_host(self, host, from_col=None):
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
        if from_col is None:
            cass_result = self._get_cf_logs_by_host().get(host, column_reversed=True)
        else:
            cass_result = self._get_cf_logs_by_host().get(host, column_reversed=True, column_start=from_col)
        return [json.loads(col_val) for _, col_val in cass_result.iteritems()]

    def list_applications(self):
        """
        Returns a list of valid applications.
        """
        def _callback():
            return [item[0] for item in self._get_cf_logs_by_app().get_range(column_count=1)]

        if self._cache_enabled:
            return _json_cache('daedalus:application_list', settings.DAEDALUS_CACHE_APP_LIST, _callback)
        else:
            return _callback()

    def list_hosts(self):
        """
        Returns a list of valid hosts.
        """
        def _callback():
            return [item[0] for item in self._get_cf_logs_by_host().get_range(column_count=1)]

        if self._cache_enabled:
            return _json_cache('daedalus:host_list', settings.DAEDALUS_CACHE_APP_LIST, _callback)
        else:
            return _callback()

    def _get_severity_count(self, severity):
        def _callback():
            count = self._get_cf_logs_by_severity().get_count(severity)
            return count

        if self._cache_enabled:
            cached_count = cache.get('daedalus:severity_count:' + severity)
            if cached_count:
                return int(cached_count)
            count = _callback()
            cache.set('daedalus:severity_count:' + severity, str(count),
                settings.DAEDALUS_CACHE_SEVERITY_COUNT)
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
                    status['query_by_application_' + app] = len(self.query_by_application(app))
                except:
                    status['query_by_application_' + app] = "error"
                    _logger.exception("query_by_application() failed for app {0}".format(app))
        except:
            status['list_applications'] = "error"
            _logger.exception("list_applications() failed")

        try:
            hosts = self.list_hosts()
            status['list_hosts'] = ", ".join(hosts)
            for a_host in hosts:
                try:
                    status['query_by_host_' + a_host] = len(self.query_by_host(a_host))
                except:
                    status['query_by_host_' + a_host] = "error"
                    _logger.exception("query_by_host() failed for host {0}".format(a_host))
        except:
            status['list_hosts'] = "error"
            _logger.exception("list_hosts() failed")

        try:
            sys_mgr = SystemManager()
            sys_mgr.describe_ring(settings.KEYSPACE)
            status['SystemManager.describe_ring(%s)' % settings.KEYSPACE] = 'ok'
        except:
            status['SystemManager.describe_ring(%s)' % settings.KEYSPACE] = 'error'
            _logger.exception("SystemManager.describe_ring() failed")
        finally:
            sys_mgr.close()

        return status

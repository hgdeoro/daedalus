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
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY, UTF8_TYPE
from pycassa.types import TimeUUIDType, CompositeType, UTF8Type, IntegerType
from pycassa.batch import Mutator
from pycassa.pool import AllServersUnavailable
from pycassa.util import convert_time_to_uuid
from pycassa.cassandra.ttypes import NotFoundException

from daedalus.utils import ymd_from_uuid1, ymd_from_epoch,\
    utc_timestamp2datetime, time_series_generator, \
    ymdhm_from_uuid1
from daedalus_client import DaedalusException

logger = logging.getLogger(__name__)

EMPTY_VALUE = ''

# TODO: this regex should be valid only for valid Cassandra row keys
APPLICATION_REGEX = re.compile(r'^[a-zA-Z0-9/-]+$')

# TODO: this regex should be valid only for valid Cassandra row keys
HOST_REGEX = re.compile(r'^[a-zA-Z0-9-\.]+$')

CF_LOGS = 'Logs'
CF_LOGS_BY_APP = 'Logs_by_app'
CF_LOGS_BY_HOST = 'Logs_by_host'
CF_LOGS_BY_SEVERITY = 'Logs_by_severity'
CF_METADATA = 'Metadata'
CF_TIMESTAMP_BITMAP = 'TimestampBitmap'
CF_MULTI_MESSAGELOGS = 'MultiMessageLogs'

SECONDS_IN_DAY = 60 * 60 * 24

MULTIMSG_STATUS_OPEN = 'OPEN'
MULTIMSG_STATUS_FINISHED_OK = 'FINISHED_OK'
MULTIMSG_STATUS_FINISHED_ERROR = 'FINISHED_ERROR'
MULTIMSG_STATUS_FINISHED_UNKNOWN = 'FINISHED_UNKNOWN'


#===============================================================================
# Entry point of the module
#===============================================================================

def get_service(*args, **kwargs):
    """
    Returns an instance of  StorageService.
    """
    #return StorageService(*args, **kwargs)
    #return StorageServiceUniqueMessagePlusReferences(*args, **kwargs)
    return StorageServiceRowPerMinute(*args, **kwargs)


@contextlib.contextmanager
def get_service_cm(*args, **kwargs):
    """
    Generates context manager for a service instance.

    Use:
        with get_service_cm() as service:
            pass
    """
    service = get_service(*args, **kwargs)
    try:
        yield service
    finally:
        service.close()


#===============================================================================
# Utility methods
#===============================================================================

def _json_cache(key, ttl, callback, *args, **kwargs):
    cached = cache.get(key)
    if cached is not None:
        return json.loads(cached)
    data = callback(*args, **kwargs)
    cache.set(key, json.dumps(data), ttl)
    return data


def _check_severity(severity):
    if severity not in ('ERROR', 'WARN', 'INFO', 'DEBUG'):
        raise(DaedalusException("Invalid value for severity: '{0}'".format(severity)))


def _check_application(application):
    if not isinstance(application, basestring):
        raise(DaedalusException("Invalid identifier for application: '{0}'".format(application)))
    if not APPLICATION_REGEX.search(application):
        raise(DaedalusException("Invalid identifier for application: '{0}'".format(application)))


def _check_host(host):
    if not isinstance(host, basestring):
        raise(DaedalusException("Invalid identifier for host: '{0}'".format(host)))
    if not HOST_REGEX.search(host):
        raise(DaedalusException("Invalid identifier for host: '{0}'".format(host)))


def _check_message(message):
    if not isinstance(message, basestring):
        raise(DaedalusException("Invalid message: '{0}'".format(message)))
    if len(message) == 0:
        raise(DaedalusException("Invalid message: message is empty"))


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


class StorageService(object):
    """
    First implementation of Storage Service.
    The logs are saved in each of the CF.

    This could be good because:
    - listing messages is fast, since all the messages are in the CF
    (listing messages of a host, or an application, or a severity)

    This could bad because:
    - al the messages are n-plicated (one copy in the main CF,
    other copy in the CF of application,other copy in the CF of host,
    other copy in the CF of severity)
    """
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

    def create_keyspace(self):
        """
        Creates the Cassandra Keyspace (if not exist)
        """
        sys_mgr = None
        try:
            sys_mgr = SystemManager()
            try:
                sys_mgr.describe_ring(settings.KEYSPACE)
            except:
                logger.info("create_keyspace(): Creating keyspace %s", settings.KEYSPACE)
                sys_mgr.create_keyspace(settings.KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})
        finally:
            if sys_mgr:
                sys_mgr.close()

    def create_cfs(self):
        """
        Creates the Cassandra Column Families (if not exist)
        """
        sys_mgr = None
        pool = None
        try:
            sys_mgr = SystemManager()
            pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
            for cf_name in [CF_LOGS, CF_LOGS_BY_APP, CF_LOGS_BY_HOST, CF_LOGS_BY_SEVERITY]:
                try:
                    cf = ColumnFamily(pool, cf_name)
                except:
                    logger.info("create_cfs(): Creating column family %s", cf_name)
                    sys_mgr.create_column_family(settings.KEYSPACE, cf_name, comparator_type=TimeUUIDType())
                    cf = ColumnFamily(pool, cf_name)
                    cf.get_count(str(uuid.uuid4()))
        finally:
            if pool:
                pool.dispose()
            if sys_mgr:
                sys_mgr.close()

    def create_keyspace_and_cfs(self):
        """
        Creates the KEYSPACE and CF
        """
        self.create_keyspace()
        self.create_cfs()

    #
    #    TODO: migrate to multiple parameters instead of single `message` parameter
    #
    #    def save_log(self, message):
    #        pool = self._get_pool()
    #
    #        application = message['application']
    #        host = message['host']
    #        severity = message['severity']
    #        timestamp = message['timestamp']
    #
    #        _check_application(application)
    #        _check_severity(severity)
    #        _check_host(host)
    #
    #        event_uuid = convert_time_to_uuid(float(timestamp), randomize=True)
    #        message['_id'] = event_uuid.get_hex()
    #        json_message = json.dumps(message)
    #
    #        with Mutator(pool) as batch:
    #            # Save on <CF> CF_LOGS
    #            row_key = ymd_from_uuid1(event_uuid)
    #            batch.insert(
    #                self._get_cf_logs(),
    #                str(row_key), {
    #                    event_uuid: json_message,
    #            })
    #
    #            # Save on <CF> CF_LOGS_BY_APP
    #            batch.insert(
    #                self._get_cf_logs_by_app(),
    #                application, {
    #                    event_uuid: json_message,
    #            })
    #
    #            # Save on <CF> CF_LOGS_BY_HOST
    #            batch.insert(
    #                self._get_cf_logs_by_host(),
    #                host, {
    #                    event_uuid: json_message,
    #            })
    #
    #            # Save on <CF> CF_LOGS_BY_SEVERITY
    #            batch.insert(
    #                self._get_cf_logs_by_severity(),
    #                severity, {
    #                    event_uuid: json_message,
    #            })

    def _get_rows_keys(self, cf):
        """
        Return all the existing keys of a cf (UNSORTED).
        """
        # FIXME: check current implementation's performance
        # BUT row-cache of Cassandra should make this query pretty fast
        return [item[0] for item in cf.get_range(column_count=1, row_count=999)]

    def query(self, from_col=None):
        """
        Returns list of dicts.
        """
        result = []

        # As of https://issues.apache.org/jira/browse/CASSANDRA-295, I think Daedalus should
        # not depend on the type of partitioner configured, since it's configured cluster-wide
        # and since RandomPartitioner is the default and sugested, we should work with it.

        def _callback():
            _row_keys = self._get_rows_keys(self._get_cf_logs())
            return sorted(_row_keys, reverse=True)

        if self._cache_enabled:
            row_keys = _json_cache('daedalus:cf_logs_keys', settings.DAEDALUS_CACHE_CF_LOGS_KEYS, _callback)
        else:
            row_keys = _callback()

        for row_key in row_keys:
            try:
                ignore_first = False
                if from_col is None:
                    cass_result = self._get_cf_logs().get(row_key, column_reversed=True)
                else:
                    cass_result = self._get_cf_logs().get(row_key, column_reversed=True,
                        column_start=from_col, column_count=101)
                    ignore_first = True

                for _, col_val in cass_result.iteritems():
                    if ignore_first:
                        ignore_first = False
                        continue
                    if len(result) < 100:
                        result.append(json.loads(col_val))
                    else:
                        return result
            except NotFoundException:
                # FIXME: try to avoid this kind of exception starting the search in the right row
                # logger.exception("---------- NotFoundException {0} ----------".format(row_key))
                pass

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

    def _generate_chart_data(self, granularity, count):

        counts = []
        time_series_limits = time_series_generator(granularity, count)

        def _compute_count(a_range):
            column_start = convert_time_to_uuid(a_range[0], lowest_val=True)
            # start_datetime = utc_timestamp2datetime(a_range[0])
            column_finish = convert_time_to_uuid(a_range[1], lowest_val=False)
            # end_datetime = utc_timestamp2datetime(a_range[1])
            row_key = ymd_from_epoch(float(a_range[0]))
            count = self._get_cf_logs().get_count(
                row_key,
                column_start=column_start,
                column_finish=column_finish)

            return count # to be used by `_json_cache()`

        for a_range in time_series_limits:
            start_datetime = utc_timestamp2datetime(a_range[0])
            end_datetime = utc_timestamp2datetime(a_range[1])

            # Whe shouldn't use cache for the last period
            if self._cache_enabled and a_range != time_series_limits[-1]:
                cache_key = "daedalus:chart:{0}-{1}".format(a_range[0], a_range[1])
                count = _json_cache(cache_key,
                    60,
                    _compute_count, a_range)
            else:
                count = _compute_count(a_range)

            counts.append((start_datetime, end_datetime, count,))

        return counts

    def generate_6hs_charts_data(self):
        """
        Returns the data from the last 6 hours.
        """
        FIVE_MIN = 60 * 5
        return self._generate_chart_data(FIVE_MIN, 12 * 6)

    def generate_24hs_charts_data(self):
        """
        Returns the data from the last 24 hours.
        """
        TWENTY_MIN = 60 * 20
        return self._generate_chart_data(TWENTY_MIN, 3 * 24)

    def generate_48hs_charts_data(self):
        """
        Returns the data from the last 48 hours.
        """
        THIRTY_MIN = 60 * 30
        return self._generate_chart_data(THIRTY_MIN, 2 * 48)

    def generate_7d_charts_data(self):
        """
        Returns the data from the last 7 days.
        """
        TWO_HOURS = 60 * 60 * 2 # 6 per day
        return self._generate_chart_data(TWO_HOURS, 6 * 7)

    #    def column_key_to_str(self, col_key):
    #        """
    #        Serializes a log message id (Cassandra column key) to a string.
    #        """
    #        return col_key.get_hex()

    def str_to_column_key(self, str_key):
        """
        De-serializes a string to be used as a log message id (Cassandra column key).
        """
        if str_key is None:
            return None
        return uuid.UUID(hex=str_key)


class StorageServiceUniqueMessagePlusReferences(StorageService):
    """
    A second implementation of Storage Service.
    With this implementation, the logs are saved only once,
    on CF_LOGS. In the other CFs, an empty column value is inserted.

    The messages are saved only once, and the other CF have 'references'
    to the messages in the mail CF.

    This could be good because:
    - stores less information

    This could bad because:
    - when searching or listing using the others CF, we need an extra query
    for each message to fetch the messages contents.
    """
    # FIXME: ensure close() is called on every instance created elsewhere

    def __init__(self, *args, **kwargs):
        StorageService.__init__(self, *args, **kwargs)

    def save_log(self, application, host, severity, timestamp, message):
        """
        Saves a log message.
        Raises:
        - DaedalusException if any parameter isn't valid.
        """
        _check_application(application)
        _check_severity(severity)
        _check_host(host)
        _check_message(message)
        try:
            timestamp = float(timestamp)
        except:
            raise(DaedalusException("The timestamp '{0}' couldn't be transformed to a float".format(timestamp)))

        event_uuid = convert_time_to_uuid(timestamp, randomize=True)
        _id = event_uuid.get_hex()

        json_message = json.dumps({
            'application': application,
            'host': host,
            'severity': severity,
            'timestamp': timestamp,
            '_id': _id,
            'message': message,
        })

        pool = self._get_pool()
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
                    event_uuid: EMPTY_VALUE,
            })

            # Save on <CF> CF_LOGS_BY_HOST
            batch.insert(
                self._get_cf_logs_by_host(),
                host, {
                    event_uuid: EMPTY_VALUE,
            })

            # Save on <CF> CF_LOGS_BY_SEVERITY
            batch.insert(
                self._get_cf_logs_by_severity(),
                severity, {
                    event_uuid: EMPTY_VALUE,
            })

    def _get_from_logs_cf(self, columns_keys):
        if not columns_keys:
            return []
        result = []
        mapped_row_keys = {}
        for a_column_key in columns_keys:
            row_key = ymd_from_uuid1(a_column_key)
            if row_key in mapped_row_keys:
                mapped_row_keys[row_key].append(a_column_key)
            else:
                mapped_row_keys[row_key] = [a_column_key]

        for a_row_key in sorted(mapped_row_keys.keys(), reverse=True):
            cass_result_from_logs = self._get_cf_logs().get(a_row_key, columns=mapped_row_keys[a_row_key])
            #ordered_result = [(val[1], key, val[0], ) for key, val in cass_result_from_logs.iteritems()]
            #ordered_result = sorted(ordered_result, reverse=True)
            #result = result + [json.loads(col_val) for _, _, col_val in ordered_result]
            result = result + [json.loads(col_val) for _, col_val in cass_result_from_logs.iteritems()]

        return sorted(result, key=lambda msg: float(msg['timestamp']), reverse=True)

    def query_by_severity(self, severity, from_col=None):
        """
        Returns list of dicts.
        """
        _check_severity(severity)
        try:
            if from_col is None:
                cass_result = self._get_cf_logs_by_severity().get(severity, column_reversed=True)
                cols_keys = [col_key for col_key, _ in cass_result.iteritems()]
            else:
                cass_result = self._get_cf_logs_by_severity().get(severity, column_reversed=True,
                    column_start=from_col, column_count=101)
                cols_keys = [col_key for col_key, _ in cass_result.iteritems()]
                if cols_keys:
                    cols_keys = cols_keys[1:]
        except NotFoundException:
            return []

        return self._get_from_logs_cf(cols_keys)

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
            cols_keys = [col_key for col_key, _ in cass_result.iteritems()]
        else:
            cass_result = self._get_cf_logs_by_app().get(application, column_reversed=True,
                column_start=from_col, column_count=101)
            cols_keys = [col_key for col_key, _ in cass_result.iteritems()]
            if cols_keys:
                cols_keys = cols_keys[1:]
        return self._get_from_logs_cf(cols_keys)

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
            cols_keys = [col_key for col_key, _ in cass_result.iteritems()]
        else:
            cass_result = self._get_cf_logs_by_host().get(host, column_reversed=True,
                column_start=from_col, column_count=101)
            cols_keys = [col_key for col_key, _ in cass_result.iteritems()]
            if cols_keys:
                cols_keys = cols_keys[1:]
        return self._get_from_logs_cf(cols_keys)


class StorageServiceRowPerMinute(StorageService):
    """
    A third implementation of Storage Service.
    With this implementation, the logs are saved only once,
    on CF_LOGS, using a CompositeKey

    This could be good because:
    - Uses many rows, this raises the posibility of well balanced clusters

    This could bad because:
    - the service is more complex
    """
    # FIXME: ensure close() is called on every instance created elsewhere

    def __init__(self, *args, **kwargs):
        StorageService.__init__(self, *args, **kwargs)
        self._app_cache = {}
        self._host_cache = {}
        self._timestamp_bitmap_cache = {}
        # METADATA cf has 2 rows:
        # - applications
        # - hosts
        self._cf_metadata = None
        self._cf_timestamp_bitmap = None
        self._cf_multi_messsagelogs = None

    def _get_cf_metadata(self):
        if self._cf_metadata is None:
            self._cf_metadata = ColumnFamily(self._get_pool(), CF_METADATA)
        return self._cf_metadata

    def _get_cf_timestamp_bitmap(self):
        if self._cf_timestamp_bitmap is None:
            self._cf_timestamp_bitmap = ColumnFamily(self._get_pool(), CF_TIMESTAMP_BITMAP)
        return self._cf_timestamp_bitmap

    def _get_cf_multi_messsagelogs(self):
        if self._cf_multi_messsagelogs is None:
            self._cf_multi_messsagelogs = ColumnFamily(self._get_pool(), CF_MULTI_MESSAGELOGS)
        return self._cf_multi_messsagelogs

    def create_cfs(self):
        """
        Creates the Cassandra Column Families (if not exist)
        """
        sys_mgr = None
        pool = None
        try:
            sys_mgr = SystemManager()
            pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)

            try:
                cf = ColumnFamily(pool, CF_LOGS)
            except:
                logger.info("create_cfs(): Creating column family %s", CF_LOGS)
                #========================================
                # Column key -> CompositeType
                #========================================
                # 1. UUID + Timestamp
                # 2. Host / Origin
                # 3. Application
                # 4. Severiry
                comparator = CompositeType(
                    TimeUUIDType(),
                    UTF8Type(),
                    UTF8Type(),
                    UTF8Type()
                )
                sys_mgr.create_column_family(settings.KEYSPACE,
                    CF_LOGS, comparator_type=comparator)
                cf = ColumnFamily(pool, CF_LOGS)
                # cf.get_count(str(uuid.uuid4()))

            try:
                cf = ColumnFamily(pool, CF_METADATA)
            except:
                logger.info("create_cfs(): Creating column family %s", CF_METADATA)
                sys_mgr.create_column_family(settings.KEYSPACE,
                    CF_METADATA, comparator_type=UTF8Type())
                cf = ColumnFamily(pool, CF_METADATA)
                cf.get_count(str(uuid.uuid4()))

            try:
                cf = ColumnFamily(pool, CF_TIMESTAMP_BITMAP)
            except:
                logger.info("create_cfs(): Creating column family %s", CF_TIMESTAMP_BITMAP)
                sys_mgr.create_column_family(settings.KEYSPACE,
                    CF_TIMESTAMP_BITMAP, comparator_type=IntegerType())
                cf = ColumnFamily(pool, CF_TIMESTAMP_BITMAP)

            try:
                cf = ColumnFamily(pool, CF_MULTI_MESSAGELOGS)
            except:
                logger.info("create_cfs(): Creating column family %s", CF_MULTI_MESSAGELOGS)
                sys_mgr.create_column_family(settings.KEYSPACE,
                    CF_MULTI_MESSAGELOGS, comparator_type=UTF8Type())
                cf = ColumnFamily(pool, CF_MULTI_MESSAGELOGS)

                sys_mgr.create_index(settings.KEYSPACE, CF_MULTI_MESSAGELOGS,
                    'meta:host', UTF8_TYPE, index_name='multimsg_host_index')
                sys_mgr.create_index(settings.KEYSPACE, CF_MULTI_MESSAGELOGS,
                    'meta:application', UTF8_TYPE, index_name='multimsg_application_index')
                sys_mgr.create_index(settings.KEYSPACE, CF_MULTI_MESSAGELOGS,
                    'meta:status', UTF8_TYPE, index_name='multimsg_finish_status_index')

        finally:
            if pool:
                pool.dispose()
            if sys_mgr:
                sys_mgr.close()

    def _get_bitmap_key_from_event_uuid(self, event_uuid):
        row_key = ymdhm_from_uuid1(event_uuid)
        key_for_bitmap = int(row_key)
        return key_for_bitmap

    def save_log(self, application, host, severity, timestamp, message,
        multi_message=False, multi_message_key=None):
        """
        Saves a log message.

        Raises:
        - DaedalusException if any parameter isn't valid.

        Returns:
        - tuple with (row_key, column_key, multi_message_key)
        """
        _check_application(application)
        _check_severity(severity)
        _check_host(host)
        _check_message(message)
        try:
            timestamp = float(timestamp)
        except:
            raise(DaedalusException("The timestamp '{0}' couldn't be "
                "transformed to a float".format(timestamp)))

        assert multi_message in (True, False,)

        event_uuid = convert_time_to_uuid(timestamp, randomize=True)
        column_key = (event_uuid, host, application, severity)
        _id = ','.join((event_uuid.get_hex(), host, application, severity, ))

        if not application in self._app_cache:
            self._app_cache[application] = True
            self._get_cf_metadata().insert('applications', {application: ''})

        if not host in self._host_cache:
            self._host_cache[host] = True
            self._get_cf_metadata().insert('hosts', {host: ''})

        row_key = ymdhm_from_uuid1(event_uuid)
        key_for_bitmap = int(row_key)
        if not key_for_bitmap in self._timestamp_bitmap_cache:
            self._timestamp_bitmap_cache[key_for_bitmap] = True
            self._get_cf_timestamp_bitmap().insert('timestamp_bitmap', {key_for_bitmap: ''})

        message_dict = {
            'application': application,
            'host': host,
            'severity': severity,
            'timestamp': timestamp,
            '_id': _id,
            'message': message,
        }

        if multi_message: # this message is part of a multi-message
            if multi_message_key:
                # The multi-message key was passed as parameter
                message_dict['_multi_message_key'] = multi_message_key
            else:
                message_dict['_multi_message_key'] = ','.join([row_key, _id])

        self._get_cf_logs().insert(row_key, {
            column_key: json.dumps(message_dict),
        })

        return (row_key, column_key, message_dict.get('_multi_message_key', None))

    def start_multimessage(self, application, host, severity, timestamp, message):
        """
        Starts a multi-message log and returns the identifier
        """
        row_key, column_key, multi_message_key = self.save_log(application, host, severity, timestamp,
            message, multi_message=True)
        assert row_key is not None
        assert column_key is not None
        assert multi_message_key is not None

        reference_to_msg = ','.join(list(row_key) + [str(i) for i in column_key])

        self._get_cf_multi_messsagelogs().insert(multi_message_key, {
            'meta:application': application,
            'meta:host': host,
            'meta:timestamp': timestamp,
            'meta:start_message': reference_to_msg,
            'meta:finish_message': '',
            'meta:status': MULTIMSG_STATUS_OPEN,
            'meta:last_message_received': reference_to_msg,
            reference_to_msg: '',
        })

        return multi_message_key

    def finish_multimessage(self, application, host, severity, timestamp,
        message, multi_message_key, final_status=MULTIMSG_STATUS_FINISHED_OK):

        assert final_status in (MULTIMSG_STATUS_FINISHED_ERROR, MULTIMSG_STATUS_FINISHED_OK,
            MULTIMSG_STATUS_FINISHED_UNKNOWN)

        row_key, column_key, _ = self.save_log(application, host, severity, timestamp, message,
            multi_message=True, multi_message_key=multi_message_key)
        reference_to_msg = ','.join(list(row_key) + [str(i) for i in column_key])
        self._get_cf_multi_messsagelogs().insert(multi_message_key, {
            'finish_status': MULTIMSG_STATUS_FINISHED_OK,
            'meta:finish_message': reference_to_msg,
            'meta:last_message_received': reference_to_msg,
            reference_to_msg: '',
        })

    def save_multimessage_log(self, application, host, severity, timestamp, message, multi_message_key):
        row_key, column_key, _ = self.save_log(application, host, severity, timestamp, message,
            multi_message=True, multi_message_key=multi_message_key)
        reference_to_msg = ','.join(list(row_key) + [str(i) for i in column_key])
        self._get_cf_multi_messsagelogs().insert(multi_message_key, {
            reference_to_msg: '',
            'meta:last_message_received': reference_to_msg,
        })

    def query(self, from_col=None, filter_callback=None):
        """
        Returns list of dicts.
        """
        result = []

        # As of https://issues.apache.org/jira/browse/CASSANDRA-295, I think Daedalus should
        # not depend on the type of partitioner configured, since it's configured cluster-wide
        # and since RandomPartitioner is the default and sugested, we should work with it.

        # Fist, get "minutes" with messages using bitmap
        try:
            if from_col:
                from_column_key = self._get_bitmap_key_from_event_uuid(from_col[0])
                bitmap_keys_generator = self._get_cf_timestamp_bitmap().xget('timestamp_bitmap',
                    column_start=from_column_key,
                    column_reversed=True)
            else:
                bitmap_keys_generator = self._get_cf_timestamp_bitmap().xget('timestamp_bitmap',
                    column_reversed=True)
        except NotFoundException:
            return result

        #    - ROW key -> yyyymmddhhmm
        #        + COL key -> host:app:severity:uuidtime
        #            + COL value -> json
        #        + COL key -> host:app:severity:uuidtime
        #            + COL value -> json
        #        + COL key -> host:app:severity:uuidtime
        #            + COL value -> json
        #        + COL key -> host:app:severity:uuidtime
        #            + COL value -> json

        # for row_key in row_keys:
        bitmap_keys_iter = iter(bitmap_keys_generator)
        iteration_count_control = iter(xrange(1, 101))
        # FIXME: StorageServiceRowPerMinute if the following 'while' breaks because iteration_count_control,
        # and the results == 0, could be more results (that would be accesible if
        # used 'iteration_count_control < 200'.. BUT the UI won't show the 'next>>>'
        # link to continue the pagination. This should be fixed!
        while len(result) < 100 and iteration_count_control.next() <= 100:
            try:
                bitmap_col_key, _ = bitmap_keys_iter.next()
            except StopIteration:
                break
            row_key = str(bitmap_col_key)
            try:
                if from_col is None:
                    cass_result = self._get_cf_logs().xget(row_key, column_reversed=True)
                else:
                    cass_result = self._get_cf_logs().xget(row_key, column_reversed=True,
                        column_start=from_col)

                for col_key, col_val in cass_result:
                    if from_col is not None and from_col == col_key:
                        continue
                    if filter_callback is not None and filter_callback(col_key) is False:
                        continue
                    if len(result) < 100:
                        result.append(json.loads(col_val))
                    else:
                        return result
            except NotFoundException:
                # FIXME: try to avoid this kind of exception starting the search in the right row
                # logger.exception("---------- NotFoundException {0} ----------".format(row_key))
                pass

        return result

    def query_by_severity(self, severity, from_col=None):
        def filter_callback(col_key):
            # col_key[0] -> UUID + Timestamp
            # col_key[1] -> Host / Origin
            # col_key[2] -> Application
            # col_key[3] -> Severiry
            assert col_key is not None
            return col_key[3] == severity
        return self.query(from_col, filter_callback=filter_callback)

    def query_by_application(self, application, from_col=None):
        def filter_callback(col_key):
            # col_key[0] -> UUID + Timestamp
            # col_key[1] -> Host / Origin
            # col_key[2] -> Application
            # col_key[3] -> Severiry
            assert col_key is not None
            return col_key[2] == application
        return self.query(from_col, filter_callback=filter_callback)

    def query_by_host(self, host, from_col=None):
        def filter_callback(col_key):
            # col_key[0] -> UUID + Timestamp
            # col_key[1] -> Host / Origin
            # col_key[2] -> Application
            # col_key[3] -> Severiry
            assert col_key is not None
            return col_key[1] == host
        return self.query(from_col, filter_callback=filter_callback)

    def get_error_count(self):
        # FIXME: StorageServiceRowPerMinute: IMPLEMENT
        return 0
    
    def get_warn_count(self):
        # FIXME: StorageServiceRowPerMinute: IMPLEMENT
        return 0
    
    def get_info_count(self):
        # FIXME: StorageServiceRowPerMinute: IMPLEMENT
        return 0
    
    def get_debug_count(self):
        # FIXME: StorageServiceRowPerMinute: IMPLEMENT
        return 0

    def list_applications(self):
        """
        Returns a list of valid applications.
        """
        return self._get_cf_metadata().get('applications', column_count=999).keys()

    def list_hosts(self):
        """
        Returns a list of valid hosts.
        """
        return self._get_cf_metadata().get('hosts', column_count=999).keys()

    def get_by_id(self, message_id):
        # FIXME: add documentation
        # FIXME: add tests
        column_key = self.str_to_column_key(message_id)
        row_key = ymdhm_from_uuid1(column_key[0])
        try:
            json_str = self._get_cf_logs().get(row_key, columns=[column_key])[column_key]
        except NotFoundException:
            return None
        return json.loads(json_str)

    def column_key_to_str(self, column_key):
        """
        Serializes a column key to a string
        """
        assert isinstance(column_key, (list, tuple, ))
        assert len(column_key) == 4
        # column_key = (event_uuid, host, application, severity)
        event_uuid, host, application, severity = column_key
        _id = ','.join((event_uuid.get_hex(), host, application, severity, ))
        return _id

    def str_to_column_key(self, str_key):
        """
        De-serializes a string to be used as a log message id (Cassandra column key).
        """
        if str_key is None:
            return None
        splitted = str_key.split(',')
        return (uuid.UUID(hex=splitted[0]), splitted[1], splitted[2], splitted[3],)

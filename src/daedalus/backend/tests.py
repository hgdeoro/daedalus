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

import datetime
import json
import logging
import multiprocessing
import os
import pprint
import random
import time
import uuid

from contextlib import contextmanager
from StringIO import StringIO
from django.test.testcases import TestCase, LiveServerTestCase
from django.conf import settings
from pycassa.system_manager import SystemManager
from pycassa.columnfamily import ColumnFamily
from pycassa.pool import ConnectionPool
from pycassa.util import convert_time_to_uuid, convert_uuid_to_time

from daedalus_client import DaedalusClient, DaedalusException, \
    utc_now_from_epoch as utc_now_from_epoch_from_client, \
    utc_str_timestamp as utc_str_timestamp_from_client, _main as cli_main, \
    ERROR, WARN, INFO, DEBUG

from daedalus.proto.random_log_generator import log_dict_generator
from daedalus.storage import get_service_cm, get_service,\
    StorageServiceRowPerMinute, MULTIMSG_STATUS_FINISHED_ERROR,\
    MULTIMSG_STATUS_FINISHED_OK, MULTIMSG_STATUS_FINISHED_UNKNOWN,\
    MULTIMSG_STATUS_OPEN
from daedalus.utils import utc_str_timestamp, utc_timestamp2datetime,\
    utc_now, utc_now_from_epoch, ymd_from_epoch, ymd_from_uuid1,\
    backward_time_series_generator, time_series_generator,\
    ymdhm_int_from_timestamp

logger = logging.getLogger(__name__)


def _truncate_all_column_families():
    """
    Truncates all the existing CF on the configured keyspace (settings.KEYSPACE)
    """
    sys_mgr = SystemManager()
    pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
    for cf_name, _ in sys_mgr.get_keyspace_column_families(settings.KEYSPACE).iteritems():
        logger.info("Truncating CF: '%s'...", cf_name)
        cf = ColumnFamily(pool, cf_name)
        cf.truncate()
    sys_mgr.close()
    pool.dispose()


def sparse_timestamp_generator(random_seed):
    curr_time = time.time()
    four_months = float(60 * 60 * 24 * 120)
    random_gen = random.Random(random_seed)
    while True:
        yield "{0:0.30f}".format(curr_time - (four_months * random_gen.random()))


def _bulk_save_random_messages_to_real_keyspace(max_count, timestamp_generator=None, *args, **kwargs):
    """
    Saves messages on REAL keyspace.
    Returns a tuple (item inserted, elapsed time).
    """
    settings.KEYSPACE = settings.KEYSPACE_REAL
    print "Un-patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
    return _bulk_save_random_messages_to_default_keyspace(max_count,
        timestamp_generator=timestamp_generator, *args, **kwargs)


def _bulk_save_random_messages_to_default_keyspace(max_count=None,
        timestamp_generator=None, max_rate=None):
    """
    Saves messages to the configured keyspace (settings.KEYSPACE).
    Returns a tuple (item inserted, elapsed time).
    If max_rate is not None, that value limits the insert per seconds.
    """
    start = time.time()
    count = 0
    if max_rate is not None:
        wait_between = 1.0 / float(max_rate)
    else:
        wait_between = 0.0
    with get_service_cm() as storage_service:
        storage_service.create_keyspace_and_cfs()
        try:
            logging.info("Starting insertions...")
            for message in log_dict_generator(1, timestamp_generator=timestamp_generator):
                storage_service.save_log(message['application'], message['host'], message['severity'],
                    message['timestamp'], message['message'])
                count += 1
                if max_count > 0 and count >= max_count:
                    break
                if max_rate is not None:
                    time.sleep(wait_between)
                if count % 100 == 0:
                    avg = float(count) / (time.time() - start)
                    last_message_date = str(datetime.datetime.fromtimestamp(float(message['timestamp'])))
                    logging.info("Inserted %d messages, %f insert/sec - Last message date: %s",
                        count, avg, last_message_date)
        except KeyboardInterrupt:
            logging.info("Stopping...")
    end = time.time()
    avg = float(count) / (end - start)
    logging.info("%d messages inserted. Avg: %f insert/sec", count, avg)
    return count, end - start


@contextmanager
def custom_tz(tz):
    """
    Use:
        with custom_tz("UTC-04:00"):
            do_something()
    """
    original_tz = os.environ.get('TZ', None)
    try:
        os.environ['TZ'] = tz
        yield
    finally:
        if original_tz is None:
            del os.environ['TZ']
        else:
            os.environ['TZ'] = original_tz


def run_foreach_tz(callback, tz_list=None, *args, **kwargs):
    """
    Calls `callback()` using various timezones.
    Returns the list of values returned.

    http://en.wikipedia.org/wiki/List_of_time_zones_by_UTC_offset
    """
    UTC_OFFSET_FROM = -12
    UTC_OFFSET_TO = 14
    RETURN_VALUES = []

    if tz_list:
        timezones = tz_list
    else:
        timezones = []
        for delta in range(UTC_OFFSET_FROM, UTC_OFFSET_TO + 1):
            if delta < 0:
                timezones.append('UTC-{0:02d}:30'.format(abs(delta)))
                timezones.append('UTC-{0:02d}:00'.format(abs(delta)))
            elif delta > 0:
                timezones.append('UTC+{0:02d}:00'.format(abs(delta)))
                timezones.append('UTC+{0:02d}:30'.format(abs(delta)))
            else:
                timezones.append('UTC')

    original_tz = os.environ.get('TZ', None)
    try:
        for tz in timezones:
            os.environ['TZ'] = tz
            ret_value = callback(*args, **kwargs)
            RETURN_VALUES.append(ret_value)
    finally:
        if original_tz is None:
            del os.environ['TZ']
        else:
            os.environ['TZ'] = original_tz
    return RETURN_VALUES


class BaseTestCase(TestCase):
    """
    Base class for Daedalus test cases.
    """

    def assertDatetimesEquals(self, dt1, dt2):
        self.assertEqual(dt1.year, dt2.year)
        self.assertEqual(dt1.month, dt2.month)
        self.assertEqual(dt1.day, dt2.day)
        self.assertEqual(dt1.hour, dt2.hour)
        self.assertEqual(dt1.minute, dt2.minute)
        self.assertEqual(dt1.second, dt2.second)


class StorageBaseTest(BaseTestCase):

    def setUp(self):
        self._storage_service = None

    def tearDown(self):
        if self._storage_service is not None:
            self._storage_service.close()

    def get_service(self):
        if self._storage_service is None:
            self._storage_service = get_service(cache_enabled=False)
        return self._storage_service


class StorageTest(StorageBaseTest):
    """
    Tests of the storage service.
    """

    def test_save_and_queries(self):
        _truncate_all_column_families()

        # Test storage.save_log()
        timestamp = time.time()
        message = {
            'application': u'dbus',
            'host': u'localhost',
            'severity': u"INFO",
            'message': u"Successfully activated service 'org.kde.powerdevil.backlighthelper'",
            'timestamp': "{0:0.25f}".format(timestamp),
        }
        self.get_service().save_log(**message)

        # Test storage.query()
        result = self.get_service().query()
        self.assertEqual(len(result), 1)
        retrieved_message = result[0]
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        # Test storage.query_by_severity()
        result = self.get_service().query_by_severity("INFO")
        self.assertEqual(len(result), 1)
        retrieved_message = result[0]
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        # Test storage.query_by_application()
        result = self.get_service().query_by_application("dbus")
        self.assertEqual(len(result), 1)
        retrieved_message = result[0]
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        # Test storage.query_by_host()
        result = self.get_service().query_by_host("localhost")
        self.assertEqual(len(result), 1)
        retrieved_message = result[0]
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        # Test storage.list_applications()
        apps = self.get_service().list_applications()
        self.assertListEqual(apps, ['dbus'])

        # Test storage.list_hosts()
        hosts = self.get_service().list_hosts()
        self.assertListEqual(hosts, ['localhost'])

    def test_save_500_log(self):
        """
        Saves 500 messages on the configured keyspace (settings.KEYSPACE)
        """
        _bulk_save_random_messages_to_default_keyspace(500)
        result = self.get_service().query()
        self.assertEqual(len(result), 100)

    def test_sparse_save_200_log_and_query(self):
        """
        Saves 200 messages on the configured keyspace (settings.KEYSPACE)
        """
        _bulk_save_random_messages_to_default_keyspace(200,
            timestamp_generator=sparse_timestamp_generator(0))
        result = self.get_service().query()
        self.assertEqual(len(result), 100)

    def test_queries_on_empty_db(self):
        _truncate_all_column_families()
        self.get_service().query_by_severity('ERROR')
        self.get_service().query_by_severity('WARN')
        self.get_service().query_by_severity('INFO')
        self.get_service().query_by_severity('DEBUG')

    def print_rows(self):
        settings.KEYSPACE = settings.KEYSPACE_REAL
        print "Un-patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
        try:
            cf = ColumnFamily()
        except:
            cf = self.get_service()._get_cf_logs()
        range_resp = cf.get_range(column_count=1, row_count=999)
        row_keys = [item[0] for item in range_resp]
        print row_keys
        print "Cant:", len(row_keys)

    def test_basic_generate_6hs_charts_data(self):
        # FIXME: StorageServiceRowPerMinute: remove this and implement generate_6hs_charts_data()
        if isinstance(self.get_service(), StorageServiceRowPerMinute):
            return

        _truncate_all_column_families()
        _bulk_save_random_messages_to_default_keyspace(50)
        charts_data = self.get_service().generate_6hs_charts_data()
        self.assertEqual(len(charts_data), 12 * 6)
        self.assertEqual(type(charts_data[0][0]), datetime.datetime)
        self.assertEqual(type(charts_data[0][1]), datetime.datetime)
        self.assertEqual(type(charts_data[0][2]), int)
        counts = [item[2] for item in charts_data]
        self.assertEqual(sum(counts), 50)
        self.assertEqual(charts_data[-1][2], 50)
        # pprint.pprint(charts_data)

    def test_generate_6hs_charts_data(self):
        # FIXME: StorageServiceRowPerMinute: remove this and implement generate_6hs_charts_data()
        if isinstance(self.get_service(), StorageServiceRowPerMinute):
            return

        def _backward_timestamp_generator():
            FIVE_MIN = float(60 * 5)
            now = utc_now_from_epoch()
            while True:
                yield "{0:0.30f}".format(now)
                now = now - FIVE_MIN

        # Test 1 message per time period
        _truncate_all_column_families()
        _bulk_save_random_messages_to_default_keyspace(12 * 6,
            timestamp_generator=_backward_timestamp_generator())
        charts_data = self.get_service().generate_6hs_charts_data()
        # pprint.pprint(charts_data)
        counts = [item[2] for item in charts_data]
        self.assertEqual(sum(counts), 12 * 6)
        self.assertEqual(len(set(counts)), 1)

        # This time, generate 5 hours of messages, but
        # nothing between 5th and 6th hour
        _truncate_all_column_families()
        _bulk_save_random_messages_to_default_keyspace(12 * 5,
            timestamp_generator=_backward_timestamp_generator())
        charts_data = self.get_service().generate_6hs_charts_data()
        # pprint.pprint(charts_data)
        counts = [item[2] for item in charts_data]
        self.assertEqual(sum(counts), 12 * 5)
        self.assertEqual(counts, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])


class BulkSave(StorageBaseTest):
    """
    Varios method to run bulk-saves on REAL keyspace (the keyspace used by the application)
    or the DEFAULT keyspace (the used for running the tests).
    
    This class souldn't have methos named 'test_*'!
    """

    def bulk_save_500(self):
        """
        Saves 500 messages on REAL keyspace.
        """
        logging.basicConfig(level=logging.INFO)
        _bulk_save_random_messages_to_real_keyspace(500)

    def bulk_save_until_stop(self):
        """
        Saves messages on REAL keyspace until canceled.
        """
        logging.basicConfig(level=logging.INFO)
        settings.CASSANDRA_CONNECT_RETRY_WAIT = 1
        print "Patched value of CASSANDRA_CONNECT_RETRY_WAIT to 1"
        max_rate = os.environ.get('max_rate', None)
        if max_rate:
            _bulk_save_random_messages_to_real_keyspace(0, max_rate=float(max_rate))
        else:
            _bulk_save_random_messages_to_real_keyspace(0)

    def bulk_sparse_save_until_stop(self, max_count=0):
        """
        Saves messages on REAL keyspace, with dates from a month ago to today.
        """
        logging.basicConfig(level=logging.INFO)
        settings.CASSANDRA_CONNECT_RETRY_WAIT = 1
        print "Patched value of CASSANDRA_CONNECT_RETRY_WAIT to 1"
        _bulk_save_random_messages_to_real_keyspace(max_count,
            timestamp_generator=sparse_timestamp_generator(0))

    def bulk_sparse_save_500(self):
        """
        Saves messages on REAL keyspace, with dates from a month ago to today.
        """
        self.bulk_sparse_save_until_stop(max_count=500)

    def _multiproc_bulk_save(self, insert_function, max_count=50000, concurrent_num=2):
        """
        Saves messages on REAL keyspace until canceled.
        """
        logging.basicConfig(level=logging.INFO)
        settings.CASSANDRA_CONNECT_RETRY_WAIT = 1
        print "Patched value of CASSANDRA_CONNECT_RETRY_WAIT to 1"

        def callback(queue, count):
            # ret = _bulk_save_random_messages_to_real_keyspace(count)
            ret = insert_function(count)
            queue.put(ret)

        queues = [multiprocessing.Queue() for _ in range(0, concurrent_num)]
        procs = [multiprocessing.Process(target=callback, args=[q, int(max_count / concurrent_num)])
            for q in queues]
        
        start = time.time()
        
        for p in procs:
            p.start()
        for p in procs:
            p.join()

        end = time.time()

        rets = [q.get() for q in queues]
        count = sum(ret[0] for ret in rets)
        elapsed_time = sum(ret[1] for ret in rets)
        avg = float(count) / (elapsed_time)
        avg2 = float(count) / (end - start)

        print ""
        print "Inserting {0} msg took {1:f} secs. - Avg: {2:f} msg/sec - Avg2: {3:f} msg/sec - ".format(
            count, elapsed_time, avg, avg2)
        print ""

    def bulk_save_multiproc_50000_to_real_keyspace(self):
        """
        Saves 50000 messages on REAL keyspace.
        """
        max_count = int(os.environ.get('INSERT_COUNT', '50000'))
        concurrent_procs = int(os.environ.get('CONCURRENT_PROCS', '2'))
        self._multiproc_bulk_save(_bulk_save_random_messages_to_real_keyspace,
            max_count=max_count, concurrent_num=concurrent_procs)

    def bulk_save_multiproc_50000_to_default_keyspace(self):
        """
        Saves 50000 messages on default keyspace (normally the 'test' keyspace).
        """
        max_count = int(os.environ.get('INSERT_COUNT', '50000'))
        concurrent_procs = int(os.environ.get('CONCURRENT_PROCS', '2'))
        self._multiproc_bulk_save(_bulk_save_random_messages_to_default_keyspace,
            max_count=max_count, concurrent_num=concurrent_procs)

    def bulk_save_multimsg(self):
        settings.KEYSPACE = settings.KEYSPACE_REAL
        print "Un-patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
        count = 0
        with get_service_cm() as storage_service:
            storage_service.create_keyspace_and_cfs()
            try:
                logging.info("Starting insertions...")
                msg_iter = iter(log_dict_generator(random.randint(1, 999999999),
                    timestamp_generator=sparse_timestamp_generator(random.randint(1, 999999999))))

                while True:
                    # Start a multi-message log
                    message = msg_iter.next()
                    timestamp = float(message['timestamp'])

                    multi_msg_id = storage_service.start_multimessage(
                        message['application'], message['host'], 'INFO',
                        str(timestamp), message['message'])

                    for _ in range(0, random.randint(2, 7)):
                        message = msg_iter.next()
                        timestamp += float(random.randint(5, 20))
                        storage_service.save_multimessage_log(
                            message['application'], message['host'], 'INFO',
                            str(timestamp), message['message'],
                            multimessage_id=multi_msg_id)

                    final_status = random.choice([
                        MULTIMSG_STATUS_FINISHED_OK,
                        MULTIMSG_STATUS_FINISHED_ERROR,
                        MULTIMSG_STATUS_FINISHED_UNKNOWN,
                    ])
                    message = msg_iter.next()
                    timestamp += float(random.randint(5, 20))
                    storage_service.finish_multimessage(
                        message['application'], message['host'], 'INFO',
                        str(timestamp), message['message'],
                        multimessage_id=multi_msg_id,
                        final_status=final_status)

                    storage_service.get_multimessage(multi_msg_id)

                    count += 1
                    if count % 100 == 0:
                        logging.info("Inserted %d messages", count)

            except KeyboardInterrupt:
                logging.info("Stopping...")
        logging.info("%d messages inserted.", count)


class ResetRealKeyspace(StorageBaseTest):

    def _reset_real_keyspace(self):
        """
        Resets the REAL keyspace (not the used for tests).
        To do this, the 'settings.KEYSPACE' is overwriten with
            the value of 'settings.KEYSPACE_REAL
'
        1. drops the keyspace
        2. re-creates CF
        3. insert random data
        """
        logging.basicConfig(level=logging.INFO)
        settings.KEYSPACE = settings.KEYSPACE_REAL
        print "Un-patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
        sys_mgr = SystemManager()
        try:
            logging.info("Dropping keyspace %s", settings.KEYSPACE)
            sys_mgr.drop_keyspace(settings.KEYSPACE)
        except:
            pass
        sys_mgr.close()
        self.get_service()._create_keyspace_and_cfs()
        _bulk_save_random_messages_to_real_keyspace(1000)


class MultiMessageTest(StorageBaseTest):

    def _gen_msg(self, msg):
        timestamp = time.time()
        message = {
            'application': u'os/backup',
            'host': u'host1.example.com',
            'severity': u"INFO",
            'message': msg,
            'timestamp': "{0:0.25f}".format(timestamp),
        }
        return message

    def test_save_multimessage(self):
        _truncate_all_column_families()

        for final_status in (MULTIMSG_STATUS_FINISHED_ERROR,
            MULTIMSG_STATUS_FINISHED_OK, MULTIMSG_STATUS_FINISHED_UNKNOWN):

            # ----- Start a multi-message log
            message = self._gen_msg("Backup started")
            multi_msg_id = self.get_service().start_multimessage(**message)
            self.assertEquals(len(multi_msg_id.split(',')), 5)

            multi_message = self.get_service().get_multimessage(multi_msg_id)
            self.assertTrue('application' in multi_message['meta'])
            self.assertTrue('host' in multi_message['meta'])
            self.assertTrue('timestamp' in multi_message['meta'])
            self.assertTrue('start_message' in multi_message['meta'])
            self.assertTrue('finish_message' in multi_message['meta'])
            self.assertTrue('status' in multi_message['meta'])
            self.assertTrue('last_message_received' in multi_message['meta'])
            self.assertEqual(multi_message['meta']['finish_message'], '')
            self.assertEqual(multi_message['meta']['status'], MULTIMSG_STATUS_OPEN)
            last_message_received = multi_message['meta']['last_message_received']

            # ----- Add a message
            message = self._gen_msg("Backup of database 'database1' finished OK")
            message['multimessage_id'] = multi_msg_id
            self.get_service().save_multimessage_log(**message)

            multi_message = self.get_service().get_multimessage(multi_msg_id)
            self.assertTrue('application' in multi_message['meta'])
            self.assertTrue('host' in multi_message['meta'])
            self.assertTrue('timestamp' in multi_message['meta'])
            self.assertTrue('start_message' in multi_message['meta'])
            self.assertTrue('finish_message' in multi_message['meta'])
            self.assertTrue('status' in multi_message['meta'])
            self.assertTrue('last_message_received' in multi_message['meta'])
            self.assertEqual(multi_message['meta']['finish_message'], '')
            self.assertEqual(multi_message['meta']['status'], MULTIMSG_STATUS_OPEN)
            self.assertNotEqual(last_message_received, multi_message['meta']['last_message_received'])
            last_message_received = multi_message['meta']['last_message_received']

            # ----- Finish the multi-message
            message = self._gen_msg("Backup finished OK")
            message['multimessage_id'] = multi_msg_id
            message['final_status'] = final_status
            self.get_service().finish_multimessage(**message)

            multi_message = self.get_service().get_multimessage(multi_msg_id)
            self.assertTrue('application' in multi_message['meta'])
            self.assertTrue('host' in multi_message['meta'])
            self.assertTrue('timestamp' in multi_message['meta'])
            self.assertTrue('start_message' in multi_message['meta'])
            self.assertTrue('finish_message' in multi_message['meta'])
            self.assertTrue('status' in multi_message['meta'])
            self.assertTrue('last_message_received' in multi_message['meta'])

            self.assertNotEqual(multi_message['meta']['finish_message'], '')
            self.assertEqual(multi_message['meta']['status'], final_status)
            self.assertNotEqual(last_message_received, multi_message['meta']['last_message_received'])


class WebBackendTest(TestCase):

    def test_insert_via_web(self):
        msg_dict = log_dict_generator(1).next()
        respose = self.client.post('/backend/save/', msg_dict)
        self.assertEqual(respose.status_code, 201)
        content = json.loads(respose.content)
        self.assertEquals(content['status'], 'ok')

    def _test_error_400(self, message_dict):
        respose = self.client.post('/backend/save/', message_dict)
        self.assertEqual(respose.status_code, 400)
        content = json.loads(respose.content)
        self.assertEquals(content['status'], 'error')

    def test_insert_via_web_with_invalid_timestamp(self):
        # without timestamp
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'severity': u"INFO",
            'message': u"message123'",
        })

        # with empty timestamp
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': u"",
        })

        # with invalid timestamp
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': u"sometext",
        })

    def test_insert_via_web_with_invalid_application(self):
        # without application
        self._test_error_400({
            'host': u'host123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': unicode(time.time()),
        })

        # with emtpy application
        self._test_error_400({
            'host': u'host123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': unicode(time.time()),
            'application': u"",
        })

        # with invalid application
        self._test_error_400({
            'host': u'host123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': unicode(time.time()),
            'application': u"___",
        })

    def test_insert_via_web_with_invalid_host(self):
        # without host
        self._test_error_400({
            'application': u'application123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': unicode(time.time()),
        })

        # with empty host
        self._test_error_400({
            'application': u'application123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': unicode(time.time()),
            'host': u'',
        })

        # with invalid host
        self._test_error_400({
            'application': u'application123',
            'severity': u"INFO",
            'message': u"message123'",
            'timestamp': unicode(time.time()),
            'host': u'___',
        })

    def test_insert_via_web_with_invalid_severity(self):
        # without severity
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'message': u"message123'",
            'timestamp': unicode(time.time()),
        })

        # with empty severity
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'message': u"message123'",
            'timestamp': unicode(time.time()),
            'severity': u"",
        })

        # with invalid severity
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'message': u"message123'",
            'timestamp': unicode(time.time()),
            'severity': u"xxx",
        })

    def test_insert_via_web_with_invalid_message(self):
        # without message
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'severity': u"INFO",
            'timestamp': unicode(time.time()),
        })

        # with empty message
        self._test_error_400({
            'application': u'application123',
            'host': u'host123',
            'severity': u"INFO",
            'timestamp': unicode(time.time()),
            'message': u"",
        })

    def test_save_100_log(self):
        self._save_random_messages_via_web(100)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Utility non-test methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _save_random_messages_via_web(self, max_count=None):
        start = time.time()
        count = 0
        try:
            for message in log_dict_generator(1):
                respose = self.client.post('/backend/save/', message)
                self.assertEqual(respose.status_code, 201)
                content = json.loads(respose.content)
                self.assertEquals(content['status'], 'ok')

                count += 1
                if count % 50 == 0:
                    avg = float(count) / (time.time() - start)
                    logging.info("Inserted %d messages, %f insert/sec", count, avg)
                    if max_count > 0 and count > max_count:
                        break
        except KeyboardInterrupt:
            logging.info("Stopping...")
        end = time.time()
        avg = float(count) / (end - start)
        logging.info("%d messages inserted. Avg: %f insert/sec", count, avg)


class TimeRelatedUtilTest(TestCase):
    """
    Tests timezone aware functions.
    """

    def test_datetime(self):
        """
        Assert that different datetimes are generated when used with `run_foreach_tz()`
        """
        def callback():
            return datetime.datetime.now()

        datetime_list = run_foreach_tz(callback)
        self.assertTrue(len(set([d.hour for d in datetime_list])) >= 12)

    def test_utc_now(self):
        """
        Assert that utc_now() returns the same date for different timezones.
        """
        def callback():
            return utc_now()

        utc_now_list = run_foreach_tz(callback)
        self.assertEqual(len(set([d.day for d in utc_now_list])), 1)
        self.assertEqual(len(set([d.hour for d in utc_now_list])), 1)

    def test_utc_now_from_epoch(self):
        def callback():
            return utc_now_from_epoch()

        timestamps = run_foreach_tz(callback)
        diffs = [abs(timestamps[0] - item) for item in timestamps]
        self.assertTrue(sum(diffs) > 0.0)
        self.assertTrue(sum(diffs) < 10.0)

    def test_utc_str_timestamp(self):

        def callback():
            return utc_str_timestamp()

        timestamps = run_foreach_tz(callback)
        diffs = [abs(float(timestamps[0]) - float(item)) for item in timestamps]
        self.assertTrue(sum(diffs) > 0.0)
        self.assertTrue(sum(diffs) < 10.0)

    def test_utc_timestamp2datetime(self):
        timestamp = utc_str_timestamp()

        def callback():
            return utc_timestamp2datetime(timestamp)

        datetimes = run_foreach_tz(callback)

        self.assertEqual(len(set([d.day for d in datetimes])), 1)
        self.assertEqual(len(set([d.hour for d in datetimes])), 1)

    def test_ymd_from_epoch(self):
        
        def callback():
            return ymd_from_epoch()

        ymd_list = run_foreach_tz(callback, tz_list=['UTC-13:00', 'UTC+13:00'])

        self.assertEqual(len(set(ymd_list)), 2)

    def test_ymd_from_uuid1(self):
        uuid1 = convert_time_to_uuid(utc_now())

        def callback():
            return ymd_from_uuid1(uuid1)

        ymd_list = run_foreach_tz(callback)
        self.assertEqual(len(set(ymd_list)), 1)

    def test_ymdhm_int_from_timestamp(self):

        # 1347237097 / Mon 10 Sep 2012 12:31:37 AM UTC
        self.assertEqual(
            ymdhm_int_from_timestamp(1347237097),
            201209100031)

        # 1347237289 / Mon 10 Sep 2012 12:34:49 AM UTC
        self.assertEqual(
            ymdhm_int_from_timestamp(1347237289),
            201209100034)

        def callback():
            return ymdhm_int_from_timestamp(1347237289)

        ymdhm_list = run_foreach_tz(callback)
        self.assertEqual(len(set(ymdhm_list)), 1)
        self.assertEqual(ymdhm_list[0], 201209100034)

    def test_time_series_generator(self):

        def _test_granularity(granularity, now, time_series):
            # pprint.pprint(time_series)
            self.assertEqual(len(time_series), 10)
            self.assertEqual(set([type(x) for x in time_series]).pop(), tuple)
            upper_limit = time_series[0][1]
            # time in `now` and the upper limit of the first element should be almost equals
            self.assertTrue(abs(upper_limit - now) < granularity + 4)
            self.assertEqual(upper_limit % granularity, 0)
            for from_timestamp, to_timestamp in time_series:
                self.assertEqual(from_timestamp + granularity, to_timestamp)
                self.assertEqual(upper_limit, to_timestamp)
                upper_limit = upper_limit - granularity

        granularities = [1, 5, 10, 15, 20, 30] # seconds
        granularities += [60, 60 * 2, 60 * 5, 60 * 10, 60 * 15, 60 * 20, 60 * 30] # minutes
        granularities += [60 * 60 * 1, 60 * 60 * 2, 60 * 60 * 6, 60 * 60 * 12] # hours
        for granularity in granularities:
            now = utc_now_from_epoch()
            backward_time_series = [x for x in backward_time_series_generator(granularity, 10)]
            time_series = time_series_generator(granularity, 10)
            _test_granularity(granularity, now, backward_time_series)
            _test_granularity(granularity, now, tuple(reversed(time_series)))


class PycassaUtilsTest(BaseTestCase):

    def test_convert_time_to_uuid_is_not_utc(self):
        """
        On version 1.6 of pycassa, `pycassa.util.convert_uuid_to_time()`
        does NOT worked with UTC when passing `datetime` arguments.

        In version 1.7, pycassa supports UTC datetimes for default.
        So, if: A = utc_now() -> convert_time_to_uuid() -> UUID ...
        ... UUID -> convert_uuid_to_time() -> B
        1) with pycassa 1.6, A != B (because pycassa doesn't work with UTF)
        2) with pycassa 1.7, A == B (since all the operation are in UTC)
        """

        def callback():
            now_utc_datetime__A = utc_now()
            uuid_from_datetime = convert_time_to_uuid(now_utc_datetime__A)
            time_from_uuid = convert_uuid_to_time(uuid_from_datetime)
            datetime_from_uuid___B = utc_timestamp2datetime(time_from_uuid)
            return (now_utc_datetime__A, datetime_from_uuid___B)

        timestamps_tuples = run_foreach_tz(callback)

        for A, B in timestamps_tuples:
            self.assertDatetimesEquals(A, B)

    def test_convert_time_to_uuid_using_epoch_works(self):
        """
        Asserts that `pycassa.util.convert_uuid_to_time()`
        DOES works with UTC when passing float timestamp arguments.
        """
        with custom_tz("UTC-04:00"):
            now_utc_timestamp = utc_now_from_epoch()
            uuid_from_datetime = convert_time_to_uuid(now_utc_timestamp)
            time_from_uuid = convert_uuid_to_time(uuid_from_datetime)
            self.assertEqual(int(now_utc_timestamp), int(time_from_uuid))


class PythonClientTest(LiveServerTestCase):

    def test(self):
        import httplib
        import urllib
        params = urllib.urlencode({
            'application': u'intranet',
            'host': u'appserver3.example.com',
            'severity': u"WARN",
            'message': u"The account 'johndoe' was locked after three login attempts.",
            'timestamp': u"1343607762.837293",
        })
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn = httplib.HTTPConnection("localhost", self.server_thread.port)
        conn.request("POST", "/backend/save/", params, headers)
        response = conn.getresponse()
        print response.read()
        conn.close()

    def test_cli_good_uses(self):
        _truncate_all_column_families()

        # ~~~~~ First simplest test of CLI ~~~~~
        test_host = str(uuid.uuid4())
        test_app = str(uuid.uuid4())
        test_msg = str(uuid.uuid4())
        result = cli_main(["-p", str(self.server_thread.port),
            "-o", test_host, "-a", test_app,
            "-m", test_msg], StringIO())
        self.assertEqual(result, 0)

        result = get_service(cache_enabled=False).query_by_host(test_host)
        self.assertTrue(test_msg in [a_msg['message'] for a_msg in result])

        result = get_service(cache_enabled=False).query_by_application(test_app)
        self.assertTrue(test_msg in [a_msg['message'] for a_msg in result])

        # ~~~~~ Test severities ~~~~~
        for sev, msg, cmdline in (
                (ERROR, str(uuid.uuid4()), '--error'),
                (WARN, str(uuid.uuid4()), '--warn'),
                (INFO, str(uuid.uuid4()), '--info'),
                (INFO, str(uuid.uuid4()), ''),
                (DEBUG, str(uuid.uuid4()), '--debug'),
            ):

            result = cli_main(["-p", str(self.server_thread.port),
                "-o", "somehost", "-a", "someapp",
                "-m", msg, cmdline], StringIO())
            self.assertEqual(result, 0)

            result = get_service(cache_enabled=False).query_by_severity(sev)
            self.assertTrue(msg in [a_msg['message'] for a_msg in result])

        # ~~~~~ Test readin from stdin ~~~~~
        stdin_msg = str(uuid.uuid4())
        fake_stdin = StringIO()
        fake_stdin.write(stdin_msg)
        fake_stdin.seek(0)
        result = cli_main(["-p", str(self.server_thread.port),
            "-o", "somehost", "-a", "someapp",
            "--show-client-exceptions",
            "--from-stdin"], fake_stdin)
        self.assertEqual(result, 0)
        result = get_service(cache_enabled=False).query_by_severity(INFO)
        self.assertTrue(stdin_msg in [a_msg['message'] for a_msg in result])

    def test_cli_bad_uses(self):
        # First check that something works
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-m", "Some message", "-o", "somehost", "-a", "someapp"], StringIO(), StringIO()), 0)

        # No host nor app
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-m", "Sample msg"], StringIO(), StringIO()), 1)

        # No host
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-m", "Sample msg", "-a", "someapp"], StringIO(), StringIO()), 1)

        # No app
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-m", "Sample msg", "-o", "somehost"], StringIO(), StringIO()), 1)

        # No msg
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-o", "somehost", "-a", "someapp"], StringIO(), StringIO()), 1)
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-m", "", "-o", "somehost", "-a", "someapp"], StringIO(), StringIO()), 1)

        # Multiple secerities
        self.assertEqual(cli_main(["-p", str(self.server_thread.port),
            "-m", "Sample msg", "-o", "somehost", "--error", "--info"], StringIO(), StringIO()), 1)


class DaedalusClientTest(LiveServerTestCase):

    def test_client(self):
        _truncate_all_column_families()
        storage_service = get_service(cache_enabled=False)
        msg_host = "somehost{0}".format(random.randint(1, 999999))
        msg_app = "someapp{0}".format(random.randint(1, 999999))
        msg_message = "this is a random message %s".format(random.randint(1, 999999))
        self.assertEquals(len(storage_service.query()), 0)

        # Create a client
        daedalus_client = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            msg_host, msg_app, raise_client_exceptions=True)

        # Send a message
        daedalus_client.send_message(msg_message, 'ERROR', msg_host, msg_app)

        def _check_message(the_msg):
            # Check the message
            self.assertEquals(the_msg['host'], msg_host)
            self.assertEquals(the_msg['application'], msg_app)
            self.assertEquals(the_msg['message'], msg_message)
            self.assertEquals(the_msg['severity'], 'ERROR')

        all_the_msg = storage_service.query()
        self.assertEquals(len(all_the_msg), 1)
        _check_message(all_the_msg[0])

        # Check filters
        all_the_msg = storage_service.query_by_application(msg_app)
        self.assertEquals(len(all_the_msg), 1)
        _check_message(all_the_msg[0])

        # Check filters
        all_the_msg = storage_service.query_by_host(msg_host)
        self.assertEquals(len(all_the_msg), 1)
        _check_message(all_the_msg[0])

        # Insert many
        for _ in xrange(0, 30):
            daedalus_client.send_message(msg_message, 'ERROR', msg_host, msg_app)

        all_the_msg = storage_service.query()
        self.assertEquals(len(all_the_msg), 31)

    def test_clients_default_host_and_app(self):
        _truncate_all_column_families()
        storage_service = get_service(cache_enabled=False)
        msg_host = "somehost{0}".format(random.randint(1, 999999))
        msg_app = "someapp{0}".format(random.randint(1, 999999))
        msg_message = "this is a random message %s".format(random.randint(1, 999999))
        self.assertEquals(len(storage_service.query()), 0)

        # Create a client
        daedalus_client = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            msg_host, msg_app, raise_client_exceptions=True)

        # Send a message
        daedalus_client.send_message(msg_message, 'ERROR')

        def _check_message(the_msg):
            # Check the message
            self.assertEquals(the_msg['host'], msg_host)
            self.assertEquals(the_msg['application'], msg_app)
            self.assertEquals(the_msg['message'], msg_message)
            self.assertEquals(the_msg['severity'], 'ERROR')

        all_the_msg = storage_service.query()
        self.assertEquals(len(all_the_msg), 1)
        _check_message(all_the_msg[0])

    def test_invalid_severity(self):
        """
        Test that no message is sent with invalid severity
        """
        _truncate_all_column_families()
        storage_service = get_service(cache_enabled=False)
        self.assertEquals(len(storage_service.query()), 0)

        # Test with -> raise_client_exceptions=True

        daedalus_client = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            'host', 'app', log_client_errors=False, raise_client_exceptions=True)

        def _send_invalid_msg():
            daedalus_client.send_message("some message", 'INVALID_SEVERITY')
            pprint.pprint(get_service(cache_enabled=False).query())
            self.assertEquals(len(storage_service.query()), 0)

        self.assertRaises(DaedalusException, _send_invalid_msg)

        # Test with -> raise_client_exceptions=False

        daedalus_client2 = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            'host', 'app', log_client_errors=False, raise_client_exceptions=False)

        daedalus_client2.send_message("some message", 'INVALID_SEVERITY')
        pprint.pprint(get_service(cache_enabled=False).query())
        self.assertEquals(len(storage_service.query()), 0)

    def test_invalid_host(self):
        _truncate_all_column_families()
        storage_service = get_service(cache_enabled=False)
        self.assertEquals(len(storage_service.query()), 0)

        # Test with -> raise_client_exceptions=True

        daedalus_client = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            'some invalid host', 'app', log_client_errors=False, raise_client_exceptions=True)

        def _send_invalid_msg():
            daedalus_client.send_message("some message", ERROR)
            pprint.pprint(get_service(cache_enabled=False).query())
            self.assertEquals(len(storage_service.query()), 0)

        self.assertRaises(DaedalusException, _send_invalid_msg)

        # Test with -> raise_client_exceptions=False

        daedalus_client2 = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            'some invalid host', 'app', log_client_errors=False, raise_client_exceptions=False)

        daedalus_client2.send_message("some message", ERROR)
        pprint.pprint(get_service(cache_enabled=False).query())
        self.assertEquals(len(storage_service.query()), 0)

    def test_custom_logger(self):
        DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            custom_logger='StdOutCustomLogger')

    def test_duplicated_functions(self):
        """
        Assert that duplicated functions on client are exactly the same from `utils`
        """
        import inspect
        self.assertEquals(
            inspect.getsource(utc_now_from_epoch),
            inspect.getsource(utc_now_from_epoch_from_client))
        self.assertEquals(
            inspect.getsource(utc_str_timestamp),
            inspect.getsource(utc_str_timestamp_from_client))


class DaedalusLoggingHandlerTest(LiveServerTestCase):

    def _gen_dict_config(self, daedalus_host, daedalus_port,
        default_message_host='somehost', default_message_app='someapp', daedalus_debug=True,
        habndler_level='WARN', logger_level='WARN', propagate=True):
        #=======================================================================
        # Setup logging with dictConfig
        # See: http://docs.python.org/library/logging.config.html#logging-config-dictschema
        #=======================================================================
        return {
            'version': 1,
            'formatters': {
                #    'formatter_id': { },
                #    'formatter_id': { },
            },
            'filters': {
                #    'filter_id': {},
                #    'filter_id': {},
            },
            'handlers': {
                'daedalus_handler': {
                    'class': 'daedalus_logging_handler.CustomHandler',
                    'level': habndler_level,
                    #    'formatter': 'formatter_id',
                    #    'filters': ['filter_id', 'filter_id'],
                    'daedalus_host': daedalus_host,
                    'daedalus_port': daedalus_port,
                    'host': default_message_host,
                    'application': default_message_app,
                    'daedalus_debug': daedalus_debug,
                    # 'custom_logger': 'StdOutCustomLogger',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['daedalus_handler'],
                    'level': logger_level,
                    'propagate': propagate,
                },
                #    'logger_id': {
                #        'level': 'xxxxxxxxx',
                #        'propagate': 'xxxxxxxxx',
                #        'filters': ['xxxxxx', 'xxxxxx'],
                #        'handlers': ['xxxxxx', 'xxxxxx'],
                #    },
            },
            'root': {
                # Same as items of 'loggers'
            },
            'incremental': False,
            'disable_existing_loggers': True,
        }

    def _test_all(self):
        self._test_debug()
        self._test_info()
        self._test_warn()
        self._test_error()

    def _assertMessagesEquals(self, messages):
        service = get_service(cache_enabled=False)
        result = service.query()

        self.assertEqual(set([msg['message'] for msg in result]),
            set(messages))

    def _test_debug(self):
        _truncate_all_column_families()
        logging.config.dictConfig(self._gen_dict_config(self.server_thread.host, self.server_thread.port,
            habndler_level='DEBUG', logger_level='DEBUG'))

        debug_msg = "This is a DEBUG message {0}.".format(uuid.uuid4())
        info_msg = "This is a INFO message {0}.".format(uuid.uuid4())
        warn_msg = "This is a WARN message {0}.".format(uuid.uuid4())
        error_msg = "This is a ERROR message {0}.".format(uuid.uuid4())

        logging.debug(debug_msg)
        logging.info(info_msg)
        logging.warn(warn_msg)
        logging.error(error_msg)

        self._assertMessagesEquals([debug_msg, info_msg, warn_msg, error_msg])

    def _test_info(self):
        _truncate_all_column_families()
        logging.config.dictConfig(self._gen_dict_config(self.server_thread.host, self.server_thread.port,
            habndler_level='INFO', logger_level='INFO'))

        debug_msg = "This is a DEBUG message {0}.".format(uuid.uuid4())
        info_msg = "This is a INFO message {0}.".format(uuid.uuid4())
        warn_msg = "This is a WARN message {0}.".format(uuid.uuid4())
        error_msg = "This is a ERROR message {0}.".format(uuid.uuid4())

        logging.debug(debug_msg)
        logging.info(info_msg)
        logging.warn(warn_msg)
        logging.error(error_msg)

        self._assertMessagesEquals([info_msg, warn_msg, error_msg])

    def _test_warn(self):
        _truncate_all_column_families()
        logging.config.dictConfig(self._gen_dict_config(self.server_thread.host, self.server_thread.port,
            habndler_level='WARN', logger_level='WARN'))

        debug_msg = "This is a DEBUG message {0}.".format(uuid.uuid4())
        info_msg = "This is a INFO message {0}.".format(uuid.uuid4())
        warn_msg = "This is a WARN message {0}.".format(uuid.uuid4())
        error_msg = "This is a ERROR message {0}.".format(uuid.uuid4())

        logging.debug(debug_msg)
        logging.info(info_msg)
        logging.warn(warn_msg)
        logging.error(error_msg)

        self._assertMessagesEquals([warn_msg, error_msg])

    def _test_error(self):
        _truncate_all_column_families()
        logging.config.dictConfig(self._gen_dict_config(self.server_thread.host, self.server_thread.port,
            habndler_level='ERROR', logger_level='ERROR'))

        debug_msg = "This is a DEBUG message {0}.".format(uuid.uuid4())
        info_msg = "This is a INFO message {0}.".format(uuid.uuid4())
        warn_msg = "This is a WARN message {0}.".format(uuid.uuid4())
        error_msg = "This is a ERROR message {0}.".format(uuid.uuid4())

        logging.debug(debug_msg)
        logging.info(info_msg)
        logging.warn(warn_msg)
        logging.error(error_msg)

        self._assertMessagesEquals([error_msg])

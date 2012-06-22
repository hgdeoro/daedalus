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
import random
import time

from django.test.testcases import TestCase, LiveServerTestCase
from django.conf import settings
from pycassa.system_manager import SystemManager
from pycassa.columnfamily import ColumnFamily
from pycassa.pool import ConnectionPool

from hgdeoro.daedalus.proto.random_log_generator import log_dict_generator
from hgdeoro.daedalus.storage import get_service_cm, get_service
from hgdeoro.daedalus.web.backend.daedalus_client import DaedalusClient

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


def sparse_time_generator(random_seed):
    curr_time = time.time()
    four_months = float(60 * 60 * 24 * 120)
    random_gen = random.Random(random_seed)
    while True:
        yield curr_time - (four_months * random_gen.random())


def _bulk_save_random_messages_to_real_keyspace(max_count, time_generator=None):
    """
    Saves messages on REAL keyspace.
    Returns a tuple (item inserted, elapsed time).
    """
    settings.KEYSPACE = settings.KEYSPACE_REAL
    print "Un-patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
    return _bulk_save_random_messages_to_default_keyspace(max_count, time_generator=time_generator)


def _bulk_save_random_messages_to_default_keyspace(max_count=None, time_generator=None):
    """
    Saves messages to the configured keyspace (settings.KEYSPACE).
    Returns a tuple (item inserted, elapsed time).
    """
    start = time.time()
    count = 0
    with get_service_cm() as storage_service:
        storage_service.create_keyspace_and_cfs()
        try:
            logging.info("Starting insertions...")
            for message in log_dict_generator(1, time_generator=time_generator):
                storage_service.save_log(message)
                count += 1
                if max_count > 0 and count > max_count:
                    break
                if count % 1000 == 0:
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


class StorageTest(TestCase):

    def setUp(self):
        self._storage_service = None

    def tearDown(self):
        if self._storage_service is not None:
            self._storage_service.close()

    def get_service(self):
        if self._storage_service is None:
            self._storage_service = get_service(cache_enabled=False)
        return self._storage_service

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
        self.get_service().save_log(message)

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
        _bulk_save_random_messages_to_default_keyspace(200, time_generator=sparse_time_generator(0))
        result = self.get_service().query()
        self.assertEqual(len(result), 100)

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


class BulkSave(StorageTest):
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
        _bulk_save_random_messages_to_real_keyspace(0)

    def bulk_sparse_save_until_stop(self, max_count=0):
        """
        Saves messages on REAL keyspace, with dates from a month ago to today.
        """
        logging.basicConfig(level=logging.INFO)
        settings.CASSANDRA_CONNECT_RETRY_WAIT = 1
        print "Patched value of CASSANDRA_CONNECT_RETRY_WAIT to 1"
        _bulk_save_random_messages_to_real_keyspace(max_count, time_generator=sparse_time_generator(0))

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


class ResetRealKeyspace(StorageTest):

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


class WebBackendTest(TestCase):

    def test_insert_via_web(self):
        _truncate_all_column_families()
        msg_dict = log_dict_generator(1).next()
        json_message = json.dumps(msg_dict)
        respose = self.client.post('/save/', {'payload': json_message})
        self.assertEqual(respose.status_code, 201)
        content = json.loads(respose.content)
        self.assertEquals(content['status'], 'ok')

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
                json_message = json.dumps(message)
                respose = self.client.post('/save/', {'payload': json_message})
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


class DaedalusClientTest(LiveServerTestCase):

    def test_client(self):
        storage_service = get_service(cache_enabled=False)
        msg_host = "somehost{0}".format(random.randint(1, 999999))
        msg_app = "someapp{0}".format(random.randint(1, 999999))
        msg_message = "this is a random message %s".format(random.randint(1, 999999))
        self.assertEquals(len(storage_service.query()), 0)

        # Create a client
        daedalus_client = DaedalusClient(self.server_thread.host, int(self.server_thread.port),
            msg_host, msg_app)

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

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
import time
import uuid

from django.test.testcases import TestCase
from django.conf import settings
from pycassa.system_manager import SystemManager
from pycassa.columnfamily import ColumnFamily
from pycassa.pool import ConnectionPool

from hgdeoro.lolog import storage
from hgdeoro.lolog.proto.random_log_generator import log_generator
from hgdeoro.lolog.utils import ymd_from_epoch

logger = logging.getLogger(__name__)


def _truncate_all_column_families():
    """
    Truncates all the existing CF on the configured keyspace (settings.KEYSPACE)
    """
    sys_mgr = SystemManager()
    for cf_name, _ in sys_mgr.get_keyspace_column_families(settings.KEYSPACE).iteritems():
        pool = ConnectionPool(settings.KEYSPACE, server_list=settings.CASSANDRA_HOSTS)
        logger.info("Truncating CF: '%s'...", cf_name)
        ColumnFamily(pool, cf_name).truncate()
    sys_mgr.close()


def _bulk_save_random_messages_to_real_keyspace(max_count):
    """
    Saves messages on REAL keyspace.
    """
    settings.KEYSPACE = settings.KEYSPACE_REAL
    print "Un-patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
    _bulk_save_random_messages_to_default_keyspace(max_count)


def _bulk_save_random_messages_to_default_keyspace(max_count=None):
    """
    Saves messages to the configured keyspace (settings.KEYSPACE)
    """
    storage.get_service().create_keyspace_and_cfs()
    start = time.time()
    count = 0
    try:
        for item in log_generator(1):
            msg = item[0]
            app = item[1]
            host = item[2]
            severity = item[3]
            message = {
                'application': app,
                'host': host,
                'severity': severity,
                'message': msg,
            }
            storage.get_service().save_log(message)
            count += 1
            if count % 100 == 0:
                avg = float(count) / (time.time() - start)
                logging.info("Inserted %d messages, %f insert/sec", count, avg)
                if max_count > 0 and count > max_count:
                    break
    except KeyboardInterrupt:
        logging.info("Stopping...")
    end = time.time()
    avg = float(count) / (end - start)
    logging.info("%d messages inserted. Avg: %f insert/sec", count, avg)


class StorageTest(TestCase):

    def test_save_and_queries(self):
        _truncate_all_column_families()

        # Test storage.save_log()
        message = {
            'application': u'dbus',
            'host': u'localhost',
            'severity': u"INFO",
            'message': u"Successfully activated service 'org.kde.powerdevil.backlighthelper'",
        }
        storage.get_service().save_log(message)

        # Test storage.query()
        result = storage.get_service().query()
        a_row = result.next()
        self.assertEqual(a_row[0], ymd_from_epoch())
        columns_iterator = a_row[1].iteritems()
        col_k, col_v = columns_iterator.next()
        self.assertEqual(type(col_k), uuid.UUID)
        retrieved_message = json.loads(col_v)
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        self.assertRaises(StopIteration, result.next)
        self.assertRaises(StopIteration, columns_iterator.next)

        # Test storage.query_by_severity()
        result = storage.get_service().query_by_severity("INFO")
        columns_iterator = result.iteritems()
        col_k, col_v = columns_iterator.next()
        retrieved_message = json.loads(col_v)
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        self.assertRaises(StopIteration, columns_iterator.next)

        # Test storage.query_by_application()
        result = storage.get_service().query_by_application("dbus")
        columns_iterator = result.iteritems()
        col_k, col_v = columns_iterator.next()
        retrieved_message = json.loads(col_v)
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        self.assertRaises(StopIteration, columns_iterator.next)

        # Test storage.query_by_host()
        result = storage.get_service().query_by_host("localhost")
        columns_iterator = result.iteritems()
        col_k, col_v = columns_iterator.next()
        retrieved_message = json.loads(col_v)
        self.assertEquals(retrieved_message['severity'], message['severity'])
        self.assertEquals(retrieved_message['host'], message['host'])
        self.assertEquals(retrieved_message['application'], message['application'])
        self.assertEquals(retrieved_message['message'], message['message'])

        self.assertRaises(StopIteration, columns_iterator.next)

        # Test storage.list_applications()
        apps = storage.get_service().list_applications()
        self.assertListEqual(apps, ['dbus'])

    def test_save_500_log(self):
        """
        Saves 500 messages on the configured keyspace (settings.KEYSPACE)
        """
        _bulk_save_random_messages_to_default_keyspace(500)

    def bulk_save_500_messages_to_real_keyspace(self):
        """
        Saves 500 messages on REAL keyspace.
        """
        logging.basicConfig(level=logging.INFO)
        _bulk_save_random_messages_to_real_keyspace(500)

    def bulk_save_messages_to_real_keyspace(self):
        """
        Saves messages on REAL keyspace until canceled.
        """
        logging.basicConfig(level=logging.INFO)
        _bulk_save_random_messages_to_real_keyspace(0)


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
        storage.get_service()._create_keyspace_and_cfs()
        _bulk_save_random_messages_to_real_keyspace(1000)


class WebBackendTest(TestCase):

    def test_insert_via_web(self):
        _truncate_all_column_families()
        json_message = json.dumps({
            'application': u'dbus',
            'host': u'localhost',
            'severity': u"INFO",
            'message': u"Successfully activated service 'org.kde.powerdevil.backlighthelper'",
        })
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
            for item in log_generator(1):
                msg = item[0]
                app = item[1]
                host = item[2]
                severity = item[3]
                message = {
                    'application': app,
                    'host': host,
                    'severity': severity,
                    'message': msg,
                }

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

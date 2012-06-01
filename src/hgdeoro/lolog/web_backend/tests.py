# -*- coding: utf-8 -*-

import json
import logging
import time

from django.test.testcases import TestCase

from hgdeoro.lolog import storage
from hgdeoro.lolog.proto.random_log_generator import log_generator


class Storagetest(TestCase):
    
    def test_save_log(self):
        message = {
            'application': u'dbus ',
            'host': u'localhost',
            'severity': u"INFO",
            'message': u"Successfully activated service 'org.kde.powerdevil.backlighthelper'",
        }
        storage.save_log(message)

    def test_save_500_log(self):
        self.stress_save_log(500)

    def stress_save_log(self, max_count=None):
        logging.basicConfig(level=logging.INFO)
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
                storage.save_log(message)
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


class WebBackendTest(TestCase):

    def test_insert(self):
        json_message = json.dumps({
            'application': u'dbus ',
            'host': u'localhost',
            'severity': u"INFO",
            'message': u"Successfully activated service 'org.kde.powerdevil.backlighthelper'",
        })
        respose = self.client.post('/save/', {'payload': json_message})
        self.assertEqual(respose.status_code, 201)
        content = json.loads(respose.content)
        self.assertEquals(content['status'], 'ok')

    def test_save_100_log(self):
        self.stress_save_log(100)

    def stress_save_log(self, max_count=None):
        logging.basicConfig(level=logging.INFO)
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

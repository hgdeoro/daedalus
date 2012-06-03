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

from django.test.testcases import TestCase
from django.core.urlresolvers import reverse

from hgdeoro.lolog.web.backend.tests import _truncate_all_column_families,\
    _bulk_save_random_messages_to_default_keyspace
from hgdeoro.lolog.web.frontend import views
from hgdeoro.lolog.proto.random_log_generator import EXAMPLE_APPS

logger = logging.getLogger(__name__)


class WebFrontendTest(TestCase):

    def test(self, max_count=1000, truncate=True):
        if truncate:
            _truncate_all_column_families()
        _bulk_save_random_messages_to_default_keyspace(max_count)

        response = self.client.get(reverse(views.home))
        self.assertTemplateUsed(response, 'index.html')

        for severity in ('ERROR', 'WARN', 'INFO', 'DEBUG'):
            logger.info("Testing search by severity: '%s'", severity)
            response = self.client.get(reverse(views.search_by_severity, args=[severity]))
            self.assertTemplateUsed(response, 'index.html')

        for app in EXAMPLE_APPS:
            logger.info("Testing search by app: '%s'", app)
            response = self.client.get(reverse(views.search_by_application, args=[app]))
            self.assertTemplateUsed(response, 'index.html')

    def repeated_test(self):
        logging.basicConfig(level=logging.INFO)
        while True:
            self.test(max_count=200, truncate=False)

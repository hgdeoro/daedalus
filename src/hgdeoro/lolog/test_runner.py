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

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings
from pycassa.system_manager import SystemManager

from hgdeoro.lolog.storage import _create_keyspace_and_cfs


class CassandraDjangoTestSuiteRunner(DjangoTestSuiteRunner):

    def __init__(self, *args, **kwargs):
        print "Instantiating CassandraDjangoTestSuiteRunner..."
        super(CassandraDjangoTestSuiteRunner, self).__init__(*args, **kwargs)

    def setup_databases(self, **kwargs):
        settings.KEYSPACE = settings.KEYSPACE_TESTS
        print "Patched value of KEYSPACE to '{0}'".format(settings.KEYSPACE)
        sys_mgr = SystemManager()
        try:
            sys_mgr.drop_keyspace(settings.KEYSPACE)
            print "Keyspace {0} droped OK".format(settings.KEYSPACE)
        except:
            pass
        # keyspace 'settings.KEYSPACE' shouldn't exists
        assert settings.KEYSPACE not in sys_mgr.list_keyspaces()
        sys_mgr.close()
        _create_keyspace_and_cfs()
        return super(CassandraDjangoTestSuiteRunner, self).setup_databases(**kwargs)

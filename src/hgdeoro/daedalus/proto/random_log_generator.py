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

import random

EXAMPLE_APPS = ['intranet', 'extranet', 'gunicorn', 'nginx-dmz']

EXAMPLE_HOSTS = ['webserver1', 'webserver2', 'webserver3',
    'dbserver1', 'dbserver2', 'dbserver3']

EXAMPLE_LOG_MESSAGES = [
    'INFO [main] 2012-05-28 21:11:08,982 CacheService.java (line 96) Initializing key cache with capacity of 50 MBs.',
    'ERROR [main] 2012-05-28 21:11:09,001 CacheService.java (line 107) Scheduling key cache save to each 14400 seconds (going to save all keys).', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,003 CacheService.java (line 121) Initializing row cache with capacity of 0 MBs and provider org.apache.cassandra.cache.SerializingCacheProvider', #@IgnorePep8
    'DEBUG [main] 2012-05-28 21:11:09,013 CacheService.java (line 133) Scheduling row cache save to each 0 seconds (going to save all keys).', #@IgnorePep8
    'WARN [main] 2012-05-28 21:11:09,339 DatabaseDescriptor.java (line 511) Found table data in data directories. Consider using the CLI to define your schema.', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,381 CommitLog.java (line 137) No commitlog files found; skipping replay',
    'ERROR [main] 2012-05-28 21:11:09,400 StorageService.java (line 412) Cassandra version: 1.1.0',
    'INFO [main] 2012-05-28 21:11:09,403 StorageService.java (line 413) Thrift API version: 19.30.0',
    'DEBUG [main] 2012-05-28 21:11:09,407 StorageService.java (line 414) CQL supported versions: 2.0.0,3.0.0-beta1 (default: 2.0.0)', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,535 StorageService.java (line 444) Loading persisted ring state',
    'INFO [main] 2012-05-28 21:11:09,563 StorageService.java (line 525) Starting up server gossip',
    'WARN [main] 2012-05-28 21:11:09,615 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-LocationInfo@919099148(121/151 serialized/live bytes, 3 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:09,623 Memtable.java (line 266) Writing Memtable-LocationInfo@919099148(121/151 serialized/live bytes, 3 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:09,878 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/LocationInfo/system-LocationInfo-hc-1-Data.db (229 bytes)', #@IgnorePep8
    'WARN [main] 2012-05-28 21:11:09,918 MessagingService.java (line 284) Starting Messaging Service on port 7000',
    'INFO [main] 2012-05-28 21:11:09,937 StorageService.java (line 552) This node will not auto bootstrap because it is configured to be a seed node.', #@IgnorePep8
    'WARN [main] 2012-05-28 21:11:09,956 StorageService.java (line 633) Generated random token 91886950145154741579326719484354188314. Random tokens will result in an unbalanced ring; see http://wiki.apache.org/cassandra/Operations', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,959 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-LocationInfo@1148428095(53/66 serialized/live bytes, 2 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:09,959 Memtable.java (line 266) Writing Memtable-LocationInfo@1148428095(53/66 serialized/live bytes, 2 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:10,113 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/LocationInfo/system-LocationInfo-hc-2-Data.db (163 bytes)', #@IgnorePep8
    'DEBUG [main] 2012-05-28 21:11:10,121 StorageService.java (line 1085) Node localhost/127.0.0.1 state jump to normal', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,124 StorageService.java (line 655) Bootstrap/Replace/Move completed! Now serving reads.', #@IgnorePep8
    'WARN [main] 2012-05-28 21:11:10,128 Mx4jTool.java (line 72) Will not load MX4J, mx4j-tools.jar is not in the classpath', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,181 CassandraDaemon.java (line 124) Binding thrift service to localhost/127.0.0.1:9160', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,186 CassandraDaemon.java (line 133) Using TFastFramedTransport with a max frame size of 15728640 bytes.', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,191 CassandraDaemon.java (line 160) Using synchronous/threadpool thrift server on localhost/127.0.0.1 : 9160', #@IgnorePep8
    'INFO [Thread-2] 2012-05-28 21:11:10,192 CassandraDaemon.java (line 212) Listening for thrift clients...',
    'ERROR [MigrationStage:1] 2012-05-28 21:16:48,234 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-schema_keyspaces@1016134149(183/228 serialized/live bytes, 4 ops)', #@IgnorePep8
    'DEBUG [FlushWriter:2] 2012-05-28 21:16:48,235 Memtable.java (line 266) Writing Memtable-schema_keyspaces@1016134149(183/228 serialized/live bytes, 4 ops)', #@IgnorePep8
    'INFO [FlushWriter:2] 2012-05-28 21:16:48,434 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/schema_keyspaces/system-schema_keyspaces-hc-1-Data.db (238 bytes)', #@IgnorePep8
    'WARN [MigrationStage:1] 2012-05-28 21:22:18,572 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-schema_columnfamilies@2087463062(1138/1422 serialized/live bytes, 20 ops)', #@IgnorePep8
    'INFO [FlushWriter:3] 2012-05-28 21:22:18,575 Memtable.java (line 266) Writing Memtable-schema_columnfamilies@2087463062(1138/1422 serialized/live bytes, 20 ops)', #@IgnorePep8
    'ERROR [FlushWriter:3] 2012-05-28 21:22:18,750 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/schema_columnfamilies/system-schema_columnfamilies-hc-1-Data.db (1201 bytes)', #@IgnorePep8
]


def log_generator(seed):
    """
    Generator. In each iteration returns a list with:
    - log message
    - application
    - host
    - severity
    
    Use:
        for item in log_generator(1):
            msg = item[0]
            app = item[1]
            host = item[2]
            severity = item[3]
    """
    rnd_inst = random.Random()
    rnd_inst.seed(seed)
    while True:
        app = rnd_inst.choice(EXAMPLE_APPS)
        full_msg = rnd_inst.choice(EXAMPLE_LOG_MESSAGES)
        splitted = [item for item in full_msg.split() if item]
        host = rnd_inst.choice(EXAMPLE_HOSTS)
        severity = splitted[0]
        msg = "{0}|{1}|{2}|{3}".format(severity, host, app, ' '.join(splitted[5:]))
        yield (msg, app, host, severity, )

# -*- coding: utf-8 -*-

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import logging
import os
import random
import uuid

from pycassa import ConnectionPool, ColumnFamily
from pycassa.system_manager import SystemManager, SIMPLE_STRATEGY
import time

KEYSPACE = 'lolog'
CF_LOGS = 'Logs'

EXAMPLE_APPS = ['intranet', 'extranet', 'webserver', 'linux-webserver', 'linux-appserver']
EXAMPLE_LOG_MESSAGES = [
    'INFO [main] 2012-05-28 21:11:08,982 CacheService.java (line 96) Initializing key cache with capacity of 50 MBs.',
    'INFO [main] 2012-05-28 21:11:09,001 CacheService.java (line 107) Scheduling key cache save to each 14400 seconds (going to save all keys).', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,003 CacheService.java (line 121) Initializing row cache with capacity of 0 MBs and provider org.apache.cassandra.cache.SerializingCacheProvider', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,013 CacheService.java (line 133) Scheduling row cache save to each 0 seconds (going to save all keys).', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,339 DatabaseDescriptor.java (line 511) Found table data in data directories. Consider using the CLI to define your schema.', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,381 CommitLog.java (line 137) No commitlog files found; skipping replay',
    'INFO [main] 2012-05-28 21:11:09,400 StorageService.java (line 412) Cassandra version: 1.1.0',
    'INFO [main] 2012-05-28 21:11:09,403 StorageService.java (line 413) Thrift API version: 19.30.0',
    'INFO [main] 2012-05-28 21:11:09,407 StorageService.java (line 414) CQL supported versions: 2.0.0,3.0.0-beta1 (default: 2.0.0)', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,535 StorageService.java (line 444) Loading persisted ring state',
    'INFO [main] 2012-05-28 21:11:09,563 StorageService.java (line 525) Starting up server gossip',
    'INFO [main] 2012-05-28 21:11:09,615 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-LocationInfo@919099148(121/151 serialized/live bytes, 3 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:09,623 Memtable.java (line 266) Writing Memtable-LocationInfo@919099148(121/151 serialized/live bytes, 3 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:09,878 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/LocationInfo/system-LocationInfo-hc-1-Data.db (229 bytes)', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,918 MessagingService.java (line 284) Starting Messaging Service on port 7000',
    'INFO [main] 2012-05-28 21:11:09,937 StorageService.java (line 552) This node will not auto bootstrap because it is configured to be a seed node.', #@IgnorePep8
    'WARN [main] 2012-05-28 21:11:09,956 StorageService.java (line 633) Generated random token 91886950145154741579326719484354188314. Random tokens will result in an unbalanced ring; see http://wiki.apache.org/cassandra/Operations', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:09,959 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-LocationInfo@1148428095(53/66 serialized/live bytes, 2 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:09,959 Memtable.java (line 266) Writing Memtable-LocationInfo@1148428095(53/66 serialized/live bytes, 2 ops)', #@IgnorePep8
    'INFO [FlushWriter:1] 2012-05-28 21:11:10,113 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/LocationInfo/system-LocationInfo-hc-2-Data.db (163 bytes)', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,121 StorageService.java (line 1085) Node localhost/127.0.0.1 state jump to normal', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,124 StorageService.java (line 655) Bootstrap/Replace/Move completed! Now serving reads.', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,128 Mx4jTool.java (line 72) Will not load MX4J, mx4j-tools.jar is not in the classpath', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,181 CassandraDaemon.java (line 124) Binding thrift service to localhost/127.0.0.1:9160', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,186 CassandraDaemon.java (line 133) Using TFastFramedTransport with a max frame size of 15728640 bytes.', #@IgnorePep8
    'INFO [main] 2012-05-28 21:11:10,191 CassandraDaemon.java (line 160) Using synchronous/threadpool thrift server on localhost/127.0.0.1 : 9160', #@IgnorePep8
    'INFO [Thread-2] 2012-05-28 21:11:10,192 CassandraDaemon.java (line 212) Listening for thrift clients...',
    'INFO [MigrationStage:1] 2012-05-28 21:16:48,234 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-schema_keyspaces@1016134149(183/228 serialized/live bytes, 4 ops)', #@IgnorePep8
    'INFO [FlushWriter:2] 2012-05-28 21:16:48,235 Memtable.java (line 266) Writing Memtable-schema_keyspaces@1016134149(183/228 serialized/live bytes, 4 ops)', #@IgnorePep8
    'INFO [FlushWriter:2] 2012-05-28 21:16:48,434 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/schema_keyspaces/system-schema_keyspaces-hc-1-Data.db (238 bytes)', #@IgnorePep8
    'INFO [MigrationStage:1] 2012-05-28 21:22:18,572 ColumnFamilyStore.java (line 634) Enqueuing flush of Memtable-schema_columnfamilies@2087463062(1138/1422 serialized/live bytes, 20 ops)', #@IgnorePep8
    'INFO [FlushWriter:3] 2012-05-28 21:22:18,575 Memtable.java (line 266) Writing Memtable-schema_columnfamilies@2087463062(1138/1422 serialized/live bytes, 20 ops)', #@IgnorePep8
    'INFO [FlushWriter:3] 2012-05-28 21:22:18,750 Memtable.java (line 307) Completed flushing /var/opt/cassandra/data/system/schema_columnfamilies/system-schema_columnfamilies-hc-1-Data.db (1201 bytes)', #@IgnorePep8
]


def mass_insert(cf):
    rnd_inst = random.Random()
    rnd_inst.seed(1)
    start = time.time()
    count = 0
    try:
        while True:
            app = rnd_inst.choice(EXAMPLE_APPS)
            msg = rnd_inst.choice(EXAMPLE_LOG_MESSAGES)
            # severity = msg.split(' ')[0]
            cf.insert(app, {
                str(uuid.uuid4()): msg,
            })
            count += 1
            if count % 100 == 0:
                logging.info("Inserted %d columns", count)
    except KeyboardInterrupt:
        logging.info("Stopping...")
    end = time.time()
    avg = float(count) / (end - start)
    logging.info("Avg: %f insert/sec", avg)


def main():
    cassandra_host = os.environ.get('CASSANDRA_HOST', 'localhost')
    sys_mgr = SystemManager()
    try:
        sys_mgr.describe_ring(KEYSPACE)
    except:
        sys_mgr.create_keyspace(KEYSPACE, SIMPLE_STRATEGY, {'replication_factor': '1'})

    pool = ConnectionPool(KEYSPACE, server_list=[cassandra_host])
    try:
        cf = ColumnFamily(pool, CF_LOGS)
    except:
        sys_mgr.create_column_family(KEYSPACE, CF_LOGS)
        cf = ColumnFamily(pool, CF_LOGS)

    cf.get_count(str(uuid.uuid4()))
    mass_insert(cf)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

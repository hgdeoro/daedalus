Daedalus
----------------------------------------

Daedalus is client/server application. The __server__ (what receives the messages) is implemented
using __Django__. The log messages are stored in __Cassandra__. The __clients__ send the messages
using a POST messages, allowing to send messages from virtually any language.

Please, [report any issue here](https://github.com/hgdeoro/daedalus/issues).

### Server

* Backend: what receives the log messages

* Frontend: the webapp to list the messages (see [screenshots](https://github.com/hgdeoro/daedalus/wiki)). You can:
  - Filter by application
  - Filter by host
  - Filter by severity
  - Show all messages (default for home page)
  - Simplest form of pagination
  - Show line chart counting messages received

### Implemented clients

* [Python client and logging handler](http://pypi.python.org/pypi/daedalus-python-client/): to send
messages from Python or through the Python's logging framework

* [Java client and log4j appender](https://github.com/hgdeoro/daedalus-java-client): to send
messages from Java or log4j.

### Log messages

A log messages includes:

  - `message`: any string with a single or multi-line text
  - `application`: the application that generated the meessage
  - `host`: the host that generated the message
  - `severity`: the serverity of the message: one of 'DEBUG', 'INFO', 'WARN' or 'ERROR'
  - `timestamp`: seconds from EPOCH (in UTC) associated with the message.

How to manually send a message from Python:

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
        conn = httplib.HTTPConnection("localhost", "64364")
        conn.request("POST", "/backend/save/", params, headers)
        response = conn.getresponse()
        print response.read()
        conn.close()

Sending the same message using the Python client:

        msg = u"The account 'johndoe' was locked after three login attempts."
        daedalus_client = DaedalusClient("localhost", 64364)
        daedalus_client.send_message(msg, "ERROR", "appserver3.example.com", "intranet")


How to install from PYPI using virtualenv
--------------------------------------------------------------------------------

To install and run Daedalus server using `pip`, (assuming a `virtualenv` directory exists
and Cassandra running on localhost) use:

    $ ./virtualenv/bin/pip install daedalus
    $ export DJANGO_SETTINGS_MODULE=daedalus.settings
    $ ./virtualenv/bin/django-admin.py runserver

To install only the Python client (and logging handler), run:

    $ pip install daedalus-python-client


For the absolutely newby: how to install Cassandra + Daedalus in Ubuntu
--------------------------------------------------------------------------------

See [dev-scripts/install-on-ubuntu.sh](https://github.com/hgdeoro/daedalus/blob/master/dev-scripts/install-on-ubuntu.sh).

I recommend you to download and run the script in a newly created __virtual machine__ (mainly because it install many packages,
and must be run as root). The virtual machine should have at least 1GB of RAM (Cassandra may not work with less memory). The scripts
installs JDK, Cassandra, clones the Daedalus repository and launch the Django development server.

You can download this script and run it as root, or use it as a guide, copying-and-pasting each of the commans of the script in a
console or ssh session.

<!--
I recommend run this in a newly created virtual machine, since the fabric script connects 
and install all the services as root. The scripts installs Java and Cassandra, and to do
this, you must download the _bin_ installer of JDK 6u32 `jdk-6u32-linux-x64.bin`
and `apache-cassandra-1.1.2-bin.tar.gz`.

(1) Create a virtual machine of your choice (I use KVM+libvirt).

(2) Clone Daedalus using Git:

    $ git clone http://github.com/hgdeoro/daedalus
    $ cd daedalus

(3) Download the JDK installer and Cassandra, and copy/symlink them to the current directory `daedalus`.

    $ ln -s /path/to/jdk-6u32-linux-x64.bin .
    $ ln -s /path/to/apache-cassandra-1.1.2-bin.tar.gz .

(4) Download, setup and activate virtualenv:

    $ curl -o /tmp/virtualenv.py https://raw.github.com/pypa/virtualenv/master/virtualenv.py
    $ python /tmp/virtualenv.py virtualenv
    $ ./virtualenv/bin/pip install -r requirements-dev.txt
    $ . ./virtualenv/bin/activate

Install to a CentOS virtual machine:

    $ fab -f src/daedalus/fabfile.py -H root@192.168.122.61 install_centos_packages install_all

Install to a Ubuntu virtual machine:

    $ fab -f src/daedalus/fabfile.py -H root@192.168.122.61 install_ubuntu_packages install_all
-->

For developers: how to download and hack
----------------------------------------

JDK: download and install JDK 6 (needed for Cassandra).

Cassandra: [download](http://cassandra.apache.org/download/),
[install](http://wiki.apache.org/cassandra/GettingStarted) and start Cassandra.

Download from GitHub

    $ git clone http://github.com/hgdeoro/daedalus
    $ cd daedalus

Create virtualenv and install requeriments

    $ virtualenv virtualenv
    $ ./virtualenv/bin/pip install -r requirements.txt
    $ ./virtualenv/bin/pip install -r requirements-dev.txt

Run `syncdb` and `syncdb_cassandra`

    $ ./dev-scripts/manage.sh syncdb
    $ ./dev-scripts/manage.sh syncdb_cassandra

Start memchaed

    $ sudo service memcached start

Start development server

    $ ./dev-scripts/runserver.sh

By now you'll have the Django development server running.
Both the Daedalus __backend__ (the Django app that receives the logs via HTTP)
and the __frontend__ (the application used to see the logs) are started.
To use it, go to [http://127.0.0.1:64364/](http://127.0.0.1:64364/).

To create some random log messages, you could run:

    $ ./dev-scripts/bulk_save_random_messages.sh

(and press Ctrl+C twice to stop it).

The project could be imported from within Eclipse PyDev.


Not implemented right now / Ideas / TODOs
----------------------------------------

See [TODOs](TODO.md).


Cassandra
----------------------------------------

* A single keyspace holds all the column families.

* Messages are stored using 4 column families:
  - CF: Logs - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_app - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_host - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_severity - Cols[]: { uuid1/timestamp: JSON encodded message }

* Alternative format (implemented by StorageServiceUniqueMessagePlusReferences):
  - CF: Logs - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_app - Cols[]: { uuid1/timestamp: '' }
  - CF: Logs\_by\_host - Cols[]: { uuid1/timestamp: '' }
  - CF: Logs\_by\_severity - Cols[]: { uuid1/timestamp: '' }

* No SuperColumn nor secondary indexes by now.


Changelog
----------------------------------------

### v0.0.10

* Upgrade to pycassa 1.7
* Backend: new storage: StorageServiceRowPerMinute

### v0.0.9

* Frontend: added 'host' column to list of messages
* Client: implemented command line arguments for setting the severity
* Client: implemented tests for CLI
* General: automatized steps needed for creating a 'release'

### v0.0.8

* General: refactored Python package (from hgdeoro.daedalus.web.frontend/backend to daedalus.frontend/backend)
* General: changed default port from 8084 to 64364
* Frontend: implemented reset of memcache

### v0.0.7

* Client: created a command line to send log events
* Client: created a handler for the Python logging framework
* General: fixed various issues around `setup.py` and created `setup.py` for the Python client.
* General: now the Daedalus server and Python client are uploaded to PYPI


License
----------------------------------------

    #-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
    #    daedalus - Centralized log server
    #    Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
    #
    #    This file is part of daedalus.
    #
    #    daedalus is free software; you can redistribute it and/or modify
    #    it under the terms of the GNU General Public License as published by
    #    the Free Software Foundation version 2.
    #
    #    daedalus is distributed in the hope that it will be useful,
    #    but WITHOUT ANY WARRANTY; without even the implied warranty of
    #    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    #    GNU General Public License version 2 for more details.
    #
    #    You should have received a copy of the GNU General Public License
    #    along with daedalus; see the file LICENSE.txt.
    #-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

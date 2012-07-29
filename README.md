Daedalus
----------------------------------------

Daedalus is a __Django__ application to store log messages on __Cassandra__.
The messages are sent using HTTP POST.

There's a basic [wiki](https://github.com/hgdeoro/daedalus/wiki) at github.

This project is al alpha-quality stage, not recommended to be used on production systems.

It's developed on Ubuntu 12.04, and tested on CentOS 6 and Ubuntu 12.04 LTS Server virtual machines (with the help of fabric).

Click [here](https://github.com/hgdeoro/daedalus/issues) to report any issue.

Implemented functional use cases
----------------------------------------

1. Backend: Receive log messages using HTTP

2. Frontend: Show messages
  - Filter by application
  - Filter by host
  - Filter by severity
  - Show all messages (default for home page)
  - Simplest form of pagination
  - Show line chart counting messages received

3. Client: Python client to send messages using HTTP

4. Client: logging handler to integrate to the Python's logging framework

5. Client: [Java client and log4j appender](https://github.com/hgdeoro/daedalus-java-client) to send messages using HTTP.

For the curious: install in a virtual machine
----------------------------------------

See [dev-scripts/install-on-ubuntu.sh](https://github.com/hgdeoro/daedalus/blob/master/dev-scripts/install-on-ubuntu.sh).

I recommend you to download and run the script in a newly created virtual machine (mainly because it install many packages,
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

    $ fab -f src/hgdeoro/daedalus/fabfile.py -H root@192.168.122.61 install_centos_packages install_all

Install to a Ubuntu virtual machine:

    $ fab -f src/hgdeoro/daedalus/fabfile.py -H root@192.168.122.61 install_ubuntu_packages install_all
-->

For developers: how to download and hack
----------------------------------------

JDK: download and install JDK 6.

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
To use it, go to [http://127.0.0.1:8084/](http://127.0.0.1:8084/).

To create some random log messages, you could run:

    $ ./dev-scripts/bulk_save_random_messages.sh

(and press Ctrl+C twice to stop it).

The project could be imported from within Eclipse PyDev.


Current iteration goals
----------------------------------------


Not implemented right now / Ideas / TODOs
----------------------------------------

* Create a Django middleware to log exceptions

* Failover on client (if one server doesn't respond, try another)

* Test and compare performance and disk space: StorageService vs StorageService2

* Document installation procedure

* Easy deploy using Gunicorn

* Add tests with Selenium / WebDriver Plus

* Move Daedalus client to separate project

* Add check of memcache on status page

* Accept messages even when lack some field(s)

* Filter by date

* TTL of messages / automatic disposal of old messages

* Live update of search results
  - a. Update the search results while new messages arrives

* Tagging of log messages

* Search by message text

* Autentication to save messages (backend) and/or to see the messages (frontend)

General architecture
----------------------------------------

* Client + server app.

* Client:
  - Thin layer over a http client to send the messages

* Server:
  - Backend: Django app that receives the messages.
  - Frontend: Django app for viewing the messages.

* Messages sent over HTTP


Cassandra
----------------------------------------

* A single keyspace holds all the column families.

* Messages are stored using 4 column families:
  - CF: Logs - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_app - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_host - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_severity - Cols[]: { uuid1/timestamp: JSON encodded message }

* Alternative format (implemented by StorageService2):
  - CF: Logs - Cols[]: { uuid1/timestamp: JSON encodded message }
  - CF: Logs\_by\_app - Cols[]: { uuid1/timestamp: '' }
  - CF: Logs\_by\_host - Cols[]: { uuid1/timestamp: '' }
  - CF: Logs\_by\_severity - Cols[]: { uuid1/timestamp: '' }

* No SuperColumn nor secondary indexes by now.


Glosary
----------------------------------------

* Log message: structure containing:
  - message
  - application
  - host
  - severity
  - timestamp (Cassandra)


Changelog
----------------------------------------

### v0.0.7

* Created a command line to send log events
* Created a handler for the Python logging framework
* Created `setup_client.py`

### v0.0.6

* Many enhacements on fabric scripts and new tasks: `daedalus_syncdb()`, `gunicorn_launch()`
* Created `dev-scripts/install-on-ubuntu.sh` to document and automatize installation on Ubuntu
* Updated scripts on `dev-scripts/` to automatically use virtualenv if exists

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

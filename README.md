Daedalus
----------------------------------------

Daedalus is a __Django__ application to store log messages on __Cassandra__.
The messages are sent/received using HTTP POST, encoded as a JSON dictionary.

There's a basic [wiki](https://github.com/hgdeoro/daedalus/wiki) at github.

This project is al alpha-quality stage, not recommended to be used on production systems.

It's developed on Ubuntu 12.04, and now tested on a CentOS 6 and Ubuntu 12.04 LTS Server virtual machinees (with the help of fabric).

Implemented functional use cases (as of v0.0.2)
----------------------------------------

1. Backend: Receive log messages using HTTP (POST with JSON encoded message)

2. Frontend: Show messages
  - Filter by application
  - Filter by host
  - Filter by severity
  - Show all messages (default for home page)
  - Simplest form of pagination
  - Show line chart counting messages received

3. Client: Python client to send messages using HTTP (POST with JSON encoded message)


For the curious: install in a virtual machine
----------------------------------------

I recommend run this in a newly created virtual machine, since the fabric script needs to
connect to the virtual machine as root.

Create a virtual machine of your choice (I use KVM+libvirt).

Clone Daedalus using Git:

    $ git clone http://github.com/hgdeoro/daedalus
    $ cd daedalus

Setup virtualenv and activate it:

    $ virtualenv virtualenv
    $ ./virtualenv/bin/pip install -r requirements-dev.txt
    $ . ./virtualenv/bin/activate

Install to a CentOS virtual machine:

    $ fab -f src/hgdeoro/daedalus/fabfile.py -H root@192.168.122.61 install_centos_packages install_all

Install to a Ubuntu virtual machine:

    $ fab -f src/hgdeoro/daedalus/fabfile.py -H root@192.168.122.61 install_ubuntu_packages install_all


For developers: how to download and hack
----------------------------------------

Download from GitHub

    $ git clone http://github.com/hgdeoro/daedalus
    $ cd daedalus
    
Create virtualenv and install requeriments

    $ virtualenv virtualenv
    $ ./virtualenv/bin/pip install -r requirements.txt
    $ ./virtualenv/bin/pip install -r requirements-dev.txt

Run syncdb and syncdb_cassandra

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

* Test the instructions of the section 'For the curious: install in a virtual machine'

* Fix the fabric task `launch_cassandra()` so we can install Daedalus enterely from `install_all()`.


Not implemented right now / Ideas / TODOs
----------------------------------------

* Failover on client (if one server doesn't respond, try another)

* Test and compare performance and disk space: StorageService vs StorageService2

* Document installation procedure

* Easy deploy using Gunicorn

* Add tests with Selenium / WebDriver Plus

* Move Daedalus client to separate project

* Add check of memcache on status page

* Accept messages even when lack some field(s)

* Accept messages sent with POST even if the message is not JSON encoded

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

* Messages encoded using JSON


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
  - detail
  - application
  - host
  - severity
  - timestamp (Cassandra)


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

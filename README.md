Daedalus
----------------------------------------

Daedalus is a __Django__ application to store log messages on __Cassandra__.
The messages are sent/received using HTTP POST, encoded as a JSON dictionary.

There's a basic [wiki](https://github.com/hgdeoro/daedalus/wiki) at github.


Implemented functional use cases (as of v0.0.1)
----------------------------------------

1. Backend: Receive log messages using HTTP (POST with JSON encoded message)

2. Frontend: Show messages
  - Filter by application
  - Filter by host
  - Filter by severity
  - Show all messages (default for home page)
  - Simplest form of pagination

3. Client: Python client to send messages using HTTP (POST with JSON encoded message)


Current iteration goals (towards v0.0.2)
----------------------------------------

* Document installation procedure

* Make installable via virtualenv

* Move Daedalus client to separate project

* Add tests with Selenium / WebDriver Plus

* Unify backend/frontend (to make easier development and installation)

* Remove from requirements.txt requeriments for development (or split requirements.txt)

Not implemented right now / Ideas / TODOs
----------------------------------------

* Add check of memcache on status page

* Accept messages even when lack some field(s)

* Accept messages sent with POST even if the message is not JSON encoded

* Filter by date

* Proper timezone handling

* TTL of messages / automatic disposal of old messages

* Live update of search results
  - a. Update the search results while new messages arrives

* Tagging of log messages

* Search by message text

* Autentication to save messages (backend) and/or to see the messages (frontend)

* Client provided timestamps (for supporting bulk-upload of messages)


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

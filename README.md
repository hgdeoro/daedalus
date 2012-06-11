Daedalus
----------------------------------------

Daedalus is a Django application to store log messages on Cassandra.
The messages are sent/received using HTTP POST, encoded as a json dictionary.

There's a basic [wiki](https://github.com/hgdeoro/daedalus/wiki) at github.


Current iteration goals
----------------------------------------

* Simplest implementation of the server and a python client
  - TODO: Python client.
  - TODO: Paginate home page.


Next iteration
----------------------------------------

* TTL of messages

* Make installable via virtualenv


Implemented (finished or WIP) functional use cases
----------------------------------------

1. Save log messages

2. Show messages
  - a. Show by application
  - b. Show by host
  - c. Show by severity

3. Simplest form of pagination


Implemented (finished or WIP) Non-functional use cases
----------------------------------------


Not implemented right now
----------------------------------------

* Live update of search results
  - a. Update the search results while new messages arrives

* Tagging of log messages

* Search by message text

* No autentication to save messages

* No autentication to see messages

* Client provided timestamps (for supporting bulk-upload of messages)



General architecture
----------------------------------------

* Client + server app.

* Server:
  - Backend: Django app that receives the messages.
  - Frontend: Django app for viewing the messages.

* Client:
  - Thin layer over a http client to send the messages

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



Examples
----------------------------------------

* Log message
  - **Message**: Exception when invoking service
  - **Detail**: (stacktrace)
  - **Application**: intranet
  - **Host**: 192.168.91.77
  - **Severity**: FATAL
  - **Timestamp**: 1338569478



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

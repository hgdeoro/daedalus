Current iteration goals
----------------------------------------

* Implemente the server and a python client



Functional use cases
----------------------------------------

1. Save log messages

2. Search messages
  - a. Search by application
  - b. Search by host
  - c. Search by severity



Non-functional use cases
----------------------------------------



Next iteration
----------------------------------------

* TTL of messages



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

* Messages sent over HTTP

* Messages encoded using JSON



Server architecture
----------------------------------------

* Cassandra for storing the messages:
  - CF: Logs - Cols[]: { timestamp: JSON encodded message }
  - CF: Logs\_by\_app - Cols[]: { timestamp: JSON encodded message }
  - CF: Logs\_by\_host - Cols[]: { timestamp: JSON encodded message }
  - CF: Logs\_by\_severity - Cols[]: { timestamp: JSON encodded message }

* Django server for receiving the messages

* Message encoding



Client architecture
----------------------------------------

* Http client to save messages



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

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

import json

from django.http import HttpResponse

from hgdeoro.lolog import storage


def home(request):
    return HttpResponse("ok")


def save_log(request):
    #
    #* Log message
    #  - **Message**: Exception when invoking service
    #  - **Detail**: (stacktrace)
    #  - **Application**: intranet
    #  - **Host**: 192.168.91.77
    #  - **Severity**: FATAL
    #  - **Timestamp**: 1338569478
    #
    json_encoded_payload = request.POST['payload']
    message = json.loads(json_encoded_payload)
    storage.get_service().save_log(message)
    return HttpResponse(json.dumps({'status': 'ok'}), status=201)

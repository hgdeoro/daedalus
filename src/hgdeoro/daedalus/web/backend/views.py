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

import json

from django.http import HttpResponse

from hgdeoro.daedalus.storage import get_service_cm


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
    with get_service_cm() as storage_service:
        storage_service.save_log(message)
    return HttpResponse(json.dumps({'status': 'ok'}), status=201)

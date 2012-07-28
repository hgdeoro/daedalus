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
from django.views.decorators.csrf import csrf_exempt

from hgdeoro.daedalus.storage import get_service_cm


def home(request):
    return HttpResponse("Daedalus here :-D")


def error_403(request):
    return HttpResponse("Error 403 detected")


def error_404(request):
    return HttpResponse("404: the requested resource doesn't exists")


def error_500(request):
    return HttpResponse("500: internal error")


@csrf_exempt
def save_log(request):
    application = request.POST['application']
    host = request.POST['host']
    severity = request.POST['severity']
    timestamp = request.POST['timestamp']
    message = request.POST['message']

    with get_service_cm() as storage_service:
        storage_service.save_log(application, host, severity, timestamp, message)
    return HttpResponse(json.dumps({'status': 'ok'}), status=201)

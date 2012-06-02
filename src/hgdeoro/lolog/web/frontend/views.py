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

from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from pycassa.util import convert_uuid_to_time

from hgdeoro.lolog.storage import query, query_by_severity, list_applications,\
    query_by_application


def _ctx(**kwargs):
    ctx = dict(kwargs)
    ctx['app_list'] = list_applications()
    return ctx


def home(request):
    cassandra_result = query()
    result = []
    for _, columns in cassandra_result:
        for col_key, col_val in columns.iteritems():
            message = json.loads(col_val)
            message['timestamp_'] = datetime.fromtimestamp(convert_uuid_to_time(col_key))
            result.append(message)
    ctx = _ctx(result=result)
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_severity(request, severity):
    cassandra_result = query_by_severity(severity)
    result = []
    for col_key, col_val in cassandra_result.iteritems():
        message = json.loads(col_val)
        message['timestamp_'] = datetime.fromtimestamp(convert_uuid_to_time(col_key))
        result.append(message)
    ctx = _ctx(result=result)
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_application(request, application):
    cassandra_result = query_by_application(application)
    result = []
    for col_key, col_val in cassandra_result.iteritems():
        message = json.loads(col_val)
        message['timestamp_'] = datetime.fromtimestamp(convert_uuid_to_time(col_key))
        result.append(message)
    ctx = _ctx(result=result)
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))

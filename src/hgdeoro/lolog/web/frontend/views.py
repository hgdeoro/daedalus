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

from hgdeoro.lolog import storage


def _ctx(**kwargs):
    ctx = dict(kwargs)
    ctx['render_messages'] = []
    service = storage.get_service()
    try:
        ctx['app_list'] = service.list_applications()
    except:
        ctx['render_messages'].append("Error detected while trying to get application list")

    try:
        ctx['error_count'] = service.get_error_count()
    except:
        ctx['error_count'] = '?'
        ctx['render_messages'].append("Error detected while trying to get the count of ERRORs")

    try:
        ctx['warn_count'] = service.get_warn_count()
    except:
        ctx['warn_count'] = '?'
        ctx['render_messages'].append("Error detected while trying to get the count of WARNs")

    try:
        ctx['info_count'] = service.get_info_count()
    except:
        ctx['info_count'] = '?'
        ctx['render_messages'].append("Error detected while trying to get the count of INFOs")

    try:
        ctx['debug_count'] = service.get_debug_count()
    except:
        ctx['debug_count'] = '?'
        ctx['render_messages'].append("Error detected while trying to get the count of DEBUGs")

    return ctx


def home(request):
    result = []
    ctx = _ctx(result=result)
    try:
        cassandra_result = storage.get_service().query()
        for _, columns in cassandra_result:
            for col_key, col_val in columns.iteritems():
                message = json.loads(col_val)
                message['timestamp_'] = datetime.fromtimestamp(convert_uuid_to_time(col_key))
                result.append(message)
    except:
        ctx['render_messages'].append("Error detected while executing query()")
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_severity(request, severity):
    cassandra_result = storage.get_service().query_by_severity(severity)
    result = []
    for col_key, col_val in cassandra_result.iteritems():
        message = json.loads(col_val)
        message['timestamp_'] = datetime.fromtimestamp(convert_uuid_to_time(col_key))
        result.append(message)
    ctx = _ctx(result=result)
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_application(request, application):
    cassandra_result = storage.get_service().query_by_application(application)
    result = []
    for col_key, col_val in cassandra_result.iteritems():
        message = json.loads(col_val)
        message['timestamp_'] = datetime.fromtimestamp(convert_uuid_to_time(col_key))
        result.append(message)
    ctx = _ctx(result=result)
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))


def status(request):
    status_list = []
    ctx = _ctx(status_list=status_list)
    storage_status = storage.get_service().get_status()
    for key in sorted(storage_status.keys()):
        status_list.append((key, storage_status[key]))
    return HttpResponse(render_to_response('status.html',
        context_instance=RequestContext(request, ctx)))

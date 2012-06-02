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
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from hgdeoro.lolog.storage import query


def home(request):
    cassandra_result = query()
    result = []
    for _, columns in cassandra_result:
        for _, col in columns.iteritems():
            message = json.loads(col)
            result.append(message)
    ctx = {
        'result': result,
    }
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_severity(request, severity):
    cassandra_result = query()
    result = []
    for _, columns in cassandra_result:
        for _, col in columns.iteritems():
            message = json.loads(col)
            if message['severity'] == severity:
                result.append(message)
    ctx = {
        'result': result,
    }
    return HttpResponse(render_to_response('index.html',
        context_instance=RequestContext(request, ctx)))

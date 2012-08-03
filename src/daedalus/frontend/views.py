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
import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.core.cache import cache

from daedalus.storage import get_service_cm
from daedalus.utils import str_to_column_key
from django.core.urlresolvers import reverse

logger = logging.getLogger(__name__)


def _ctx(**kwargs):
    """
    Generates a context instance for rendering the Django view.
    """
    ctx = dict(kwargs)
    ctx['render_messages'] = []
    with get_service_cm() as service:
        try:
            ctx['app_list'] = service.list_applications()
        except:
            ctx['render_messages'].append("Error detected while trying to get application list")
            logger.exception(ctx['render_messages'][-1])
    
        try:
            ctx['host_list'] = service.list_hosts()
        except:
            ctx['render_messages'].append("Error detected while trying to get host list")
            logger.exception(ctx['render_messages'][-1])
    
        try:
            ctx['error_count'] = service.get_error_count()
        except:
            ctx['error_count'] = '?'
            ctx['render_messages'].append("Error detected while trying to get the count of ERRORs")
            logger.exception(ctx['render_messages'][-1])
    
        try:
            ctx['warn_count'] = service.get_warn_count()
        except:
            ctx['warn_count'] = '?'
            ctx['render_messages'].append("Error detected while trying to get the count of WARNs")
            logger.exception(ctx['render_messages'][-1])
    
        try:
            ctx['info_count'] = service.get_info_count()
        except:
            ctx['info_count'] = '?'
            ctx['render_messages'].append("Error detected while trying to get the count of INFOs")
            logger.exception(ctx['render_messages'][-1])
    
        try:
            ctx['debug_count'] = service.get_debug_count()
        except:
            ctx['debug_count'] = '?'
            ctx['render_messages'].append("Error detected while trying to get the count of DEBUGs")
            logger.exception(ctx['render_messages'][-1])

    return ctx


def home(request):
    from_col = str_to_column_key(request.GET.get('from', None))
    ctx = _ctx()
    with get_service_cm() as service:
        try:
            ctx['result'] = service.query(from_col=from_col)
            if ctx['result']:
                ctx['last_message_timestamp'] = ctx['result'][-1]['_uuid']
        except:
            ctx['render_messages'].append("Error detected while executing query()")
            logger.exception(ctx['render_messages'][-1])
    return HttpResponse(render_to_response('daedalus/frontend/index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_severity(request, severity):
    from_col = str_to_column_key(request.GET.get('from', None))
    with get_service_cm() as service:
        result = service.query_by_severity(severity, from_col=from_col)
    if result:
        last_message_timestamp = result[-1]['_uuid']
    else:
        last_message_timestamp = None
    ctx = _ctx(result=result, last_message_timestamp=last_message_timestamp,
        top_message="Showing only '{0}' messages.".format(severity))
    return HttpResponse(render_to_response('daedalus/frontend/index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_application(request, application):
    from_col = str_to_column_key(request.GET.get('from', None))
    with get_service_cm() as service:
        result = service.query_by_application(application, from_col=from_col)
    if result:
        last_message_timestamp = result[-1]['_uuid']
    else:
        last_message_timestamp = None
    ctx = _ctx(result=result, last_message_timestamp=last_message_timestamp,
        top_message="Showing only messages of application '{0}'.".format(application))
    return HttpResponse(render_to_response('daedalus/frontend/index.html',
        context_instance=RequestContext(request, ctx)))


def search_by_host(request, host):
    from_col = str_to_column_key(request.GET.get('from', None))
    with get_service_cm() as service:
        result = service.query_by_host(host, from_col=from_col)
    if result:
        last_message_timestamp = result[-1]['_uuid']
    else:
        last_message_timestamp = None
    ctx = _ctx(result=result, last_message_timestamp=last_message_timestamp,
        top_message="Showing only messages from host '{0}'.".format(host))
    return HttpResponse(render_to_response('daedalus/frontend/index.html',
        context_instance=RequestContext(request, ctx)))


def status(request):
    status_list = []
    ctx = _ctx(status_list=status_list)
    with get_service_cm(cache_enabled=False) as service:
        storage_status = service.get_status()
    for key in sorted(storage_status.keys()):
        status_list.append((key, storage_status[key]))
    return HttpResponse(render_to_response('daedalus/frontend/status.html',
        context_instance=RequestContext(request, ctx)))


def get_message_detail(request, message_id):
    with get_service_cm() as service:
        obj = service.get_by_id(message_id)
    return HttpResponse(json.dumps(obj), mimetype='application/json')


def charts(request, chart_type=None):
    ctx = _ctx()
    with get_service_cm() as service:
        if chart_type == '24hs':
            charts_data = service.generate_24hs_charts_data()
            chart_id = '24hs'
        elif chart_type == '48hs':
            charts_data = service.generate_48hs_charts_data()
            chart_id = '48hs'
        elif chart_type == '7d':
            charts_data = service.generate_7d_charts_data()
            chart_id = '7d'
        else:
            charts_data = service.generate_6hs_charts_data()
            chart_id = '6hs'
    ctx['charts_data'] = charts_data
    ctx['chart_id'] = chart_id
    return HttpResponse(render_to_response('daedalus/frontend/charts.html',
        context_instance=RequestContext(request, ctx)))


def reset_cache(request):
    cache.clear()
    return HttpResponseRedirect(reverse(home))

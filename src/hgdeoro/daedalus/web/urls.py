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

from django.conf.urls import patterns, url
from django.views.generic.simple import redirect_to
from django.conf import settings

from hgdeoro.daedalus.web.backend import views as backend_views
from hgdeoro.daedalus.web.frontend import views as frontend_views

urlpatterns = patterns('',
)

if settings.DAEDALUS_ENABLED_SUBSYSTEMS in ('backend', 'both'):
    urlpatterns += patterns('',
        url(r'^backend/save/', backend_views.save_log),
        url(r'^backend/$', backend_views.home),
    )
    handler403 = 'hgdeoro.daedalus.web.backend.views.error_403'
    handler404 = 'hgdeoro.daedalus.web.backend.views.error_404'
    handler500 = 'hgdeoro.daedalus.web.backend.views.error_500'

if settings.DAEDALUS_ENABLED_SUBSYSTEMS in ('frontend', 'both'):
    urlpatterns += patterns('',
        url(r'^$', redirect_to, {'url': '/frontend/'}), # Redirect
        url(r'^frontend/$', frontend_views.home),
        url(r'^frontend/status/', frontend_views.status),
        url(r'^frontend/search/severity/(.*)/', frontend_views.search_by_severity),
        url(r'^frontend/search/host/(.*)/', frontend_views.search_by_host),
        url(r'^frontend/search/application/(.*)/', frontend_views.search_by_application),
        url(r'^frontend/message/get/(.*)/', frontend_views.get_message_detail),
        url(r'^frontend/charts/(.+)/', frontend_views.charts),
        url(r'^frontend/charts/', frontend_views.charts),
    )

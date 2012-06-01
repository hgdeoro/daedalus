# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from hgdeoro.lolog.web_backend.views import home

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'web_backend.views.home', name='home'),
    # url(r'^web_backend/', include('web_backend.foo.urls')),

    url(r'^.*', home),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

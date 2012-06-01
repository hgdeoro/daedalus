# -*- coding: utf-8 -*-

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
    storage.save_log(message)
    return HttpResponse(json.dumps({'status': 'ok'}), status=201)

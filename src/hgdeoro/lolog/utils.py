# -*- coding: utf-8 -*-

import time

from datetime import date

from pycassa.util import convert_uuid_to_time

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def ymd_from_epoch(epoch=None):
    """
    Returns a string with the format YEAR+MONTH+DAY
    """
    if epoch is None:
        epoch = time.time()
    a_date = date.fromtimestamp(time.time())
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)


def ymd_from_uuid1(uuid1_value):
    """
    Returns a string with the format YEAR+MONTH+DAY
    """
    a_date = date.fromtimestamp(convert_uuid_to_time(uuid1_value))
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)

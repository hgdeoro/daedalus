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

import calendar
import datetime
import math
import time
import uuid

import pytz

from pycassa.util import convert_uuid_to_time


def utc_now():
    """
    Returns a `datetime` object representing current time in UTC.
    See:
        - http://pytz.sourceforge.net/#problems-with-localtime
            (...) The best and simplest solution is to stick with using UTC (...)
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def utc_now_from_epoch():
    """
    Returns a float representing the current time in seconds from epoch, as UTC.
    """
    current_time_from_epoch = time.time()
    utc_timetuple = time.gmtime(current_time_from_epoch)
    from_epoch = calendar.timegm(utc_timetuple) + math.modf(current_time_from_epoch)[0]
    return from_epoch


def utc_str_timestamp():
    """
    Returns a string representing the current time in UTC.
    The string represents a float: the seconds from EPOCH.
    """
    # First implementation. Worked OK, but found other method with better presission.
    #    utcnow = datetime.datetime.utcnow()
    #    timestamp = "{0}.{1:06}".format(calendar.timegm(utcnow.timetuple()), utcnow.microsecond)
    #    return timestamp

    # FIXME: change hardcoded '30' with the real precision of time.time()
    return "{0:0.30f}".format(utc_now_from_epoch())


def utc_timestamp2datetime(timestamp):
    """
    Converts a timestamp generated with `utc_str_timestamp()`
    to a 'timezone aware' datetime (using 'pytz').
    """
    the_date = datetime.datetime.utcfromtimestamp(float(timestamp))
    return the_date.replace(tzinfo=pytz.utc)


def ymd_from_epoch(a_time=None):
    """
    Returns a string with the format YEAR+MONTH+DAY.
    If 'a_time' is None (default) generates YMD for now.
    """
    if a_time is None:
        a_time = time.time()
    a_date = datetime.date.fromtimestamp(a_time)
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)


def ymd_from_uuid1(uuid1_value):
    """
    Returns a string with the format YEAR+MONTH+DAY
    """
    a_date = datetime.date.fromtimestamp(convert_uuid_to_time(uuid1_value))
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)


def column_key_to_str(col_key):
    """
    Serializes a column key to a string.
    """
    return col_key.get_hex()


def str_to_column_key(str_key):
    """
    De-serializes a string to be used as column key.
    """
    if str_key is None:
        return None
    return uuid.UUID(hex=str_key)


def get_posixtime(uuid1):
    """
    Convert the uuid1 timestamp to a standard posix timestamp.

    # Created by Kent Tenney on Wed, 13 Aug 2008 (MIT)
    # Taked from http://code.activestate.com/recipes/576420/ (Rev 1)
    # Licensed under the MIT License
    # As of http://en.wikipedia.org/wiki/MIT_License this is permited.
    #
    """
    assert uuid1.version == 1, ValueError('Only applies to uuid type 1')
    t = uuid1.time
    t = t - 0x01b21dd213814000
    t = t / 1e7
    return t

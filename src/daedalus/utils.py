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

import pytz

from pycassa.util import convert_uuid_to_time

SECONDS_IN_DAY = 60 * 60 * 24


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
    Returns a float timestamp representing the current time in seconds from epoch, as UTC.
    This is a UTC version of time.time()
    """
    current_time_from_epoch = time.time()
    utc_timetuple = time.gmtime(current_time_from_epoch)
    from_epoch = calendar.timegm(utc_timetuple) + math.modf(current_time_from_epoch)[0]
    return from_epoch


#def datetime_to_epoch(datetime_arg):
#    """
#    Converts a datetime to a timestamp, a float represeting seconds from epoch.
#    """
#    assert isinstance(datetime_arg, datetime.datetime)
#    return float(calendar.timegm(datetime_arg.timetuple())) + datetime_arg.microsecond / 1e6


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
    Converts a UTC timestamp generated with `utc_str_timestamp()`
    or `utc_now_from_epoch()` to a 'timezone aware' datetime (using 'pytz').

    Parameter:
    - timestamp: the timestamp, a string or float instance.
    """
    if not isinstance(timestamp, float):
        timestamp = float(timestamp)
    the_date = datetime.datetime.utcfromtimestamp(timestamp)
    return the_date.replace(tzinfo=pytz.utc)


def ymd_from_epoch(a_time=None):
    """
    Returns a string with the format YEAR+MONTH+DAY.
    If 'a_time' is None (default) generates YMD for now (in UTC).
    """
    if a_time is None:
        a_time = utc_now_from_epoch()
    a_date = datetime.date.fromtimestamp(a_time)
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)


def ymd_from_uuid1(uuid1_value):
    """
    Returns a string with the format YEAR+MONTH+DAY
    """
    # Originaly this was done with `datetime.date.fromtimestamp()`, but
    # this method works with localtime, instead of UTC.
    timestamp = convert_uuid_to_time(uuid1_value)
    a_date = utc_timestamp2datetime(timestamp)
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)


def ymdhm_int_from_timestamp(utc_timestamp):
    """
    Returns a int with the format YEAR+MONTH+DAY+HOUR+MINUTE
    """
    a_date = utc_timestamp2datetime(utc_timestamp)
    return a_date.year * 10 ** 8 + \
        a_date.month * 10 ** 6 + \
        a_date.day * 10 ** 4 + \
        a_date.hour * 10 ** 2 + \
        a_date.minute


def ymdhm_from_uuid1(uuid1_value):
    """
    Returns a string with the format YEAR+MONTH+DAY+HOUR+MINUTE
    """
    # Originaly this was done with `datetime.date.fromtimestamp()`, but
    # this method works with localtime, instead of UTC.
    timestamp = convert_uuid_to_time(uuid1_value)
    a_date = utc_timestamp2datetime(timestamp)
    return "{0:04d}{1:02d}{2:02d}{3:02d}{4:02d}".format(
        a_date.year, a_date.month, a_date.day, a_date.hour, a_date.minute)


#def get_posixtime(uuid1):
#    """
#    Convert the uuid1 timestamp to a standard posix timestamp.
#
#    # Created by Kent Tenney on Wed, 13 Aug 2008 (MIT)
#    # Taked from http://code.activestate.com/recipes/576420/ (Rev 1)
#    # Licensed under the MIT License
#    # As of http://en.wikipedia.org/wiki/MIT_License this is permited.
#    #
#    """
#    assert uuid1.version == 1, ValueError('Only applies to uuid type 1')
#    t = uuid1.time
#    t = t - 0x01b21dd213814000
#    t = t / 1e7
#    return t

def backward_time_series_generator(granularity, count):
    assert SECONDS_IN_DAY % granularity == 0
    now = int(utc_now_from_epoch())
    diff = now % granularity
    # remove `diff` from `now` to make `upper_limit` multiple of `granularity`
    upper_limit = now - diff
    # if `diff` is > 0, add `granularity` to upper_limit
    if diff > 0:
        upper_limit += granularity
    for _ in xrange(0, count):
        lower_limit = upper_limit - granularity
        yield (lower_limit, upper_limit)
        upper_limit = lower_limit


def time_series_generator(granularity, count):
    return tuple(reversed(tuple(backward_time_series_generator(granularity, count))))

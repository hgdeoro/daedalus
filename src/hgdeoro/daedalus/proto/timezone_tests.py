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

import datetime
import pytz
import calendar
import time
import os


def utc_str_timestamp():
    """
    Returns a string representing the current time in UTC
    """
    utcnow = datetime.datetime.utcnow()
    timestamp = "{0}.{1:06}".format(calendar.timegm(utcnow.timetuple()), utcnow.microsecond)
    return timestamp


def utc_timestamp2datetime(timestamp):
    """
    Converts a timestamp generated with `utc_str_timestamp()`
    to a datetime.
    """
    the_date = datetime.datetime.utcfromtimestamp(float(timestamp))
    return the_date.replace(tzinfo=pytz.utc)


def main():
    d_now = datetime.datetime.now()
    d_utcnow = datetime.datetime.utcnow()

    d_now_tz = d_now.replace(tzinfo=pytz.utc)
    d_utcnow_tz = d_utcnow.replace(tzinfo=pytz.utc)

    dates = (
        ("d_now", d_now),
        ("d_now_tz", d_now_tz),
        ("d_utcnow", d_utcnow),
        ("d_utcnow_tz", d_utcnow_tz),
    )

    print "{0:>30}: {1}".format("TZ", os.environ.get('TZ', ''))
    print "{0:>30}: {1}".format("time.time()", time.time())
    print ""

    for desc, date_var in dates:
        timestamp = "{0}.{1:06}".format(calendar.timegm(date_var.timetuple()), date_var.microsecond)
        from_timestamp = time.gmtime(float(timestamp))
        print "{0:>30}".format(desc)
        print "{0:>30}: {1}".format("type()", type(date_var))
        print "{0:>30}: {1}".format("str()", str(date_var))
        print "{0:>30}: {1}".format("utctimetuple()", date_var.utctimetuple())
        print "{0:>30}: {1}".format("calendar.timegm()", calendar.timegm(date_var.timetuple()))
        print "{0:>30}: {1}".format("microsecond", date_var.microsecond)
        print "{0:>30}: {1}".format("timestamp", timestamp)
        print "{0:>30}: {1}".format("from_timestamp", from_timestamp)
        print "{0:>30}: {1}".format("type(from_timestamp)", type(from_timestamp))
        print "{0:>30}: {1}".format("datetime.utcfromtimestamp()",
            datetime.datetime.utcfromtimestamp(float(timestamp)))
        print ""

    current_utc_str_timestamp = utc_str_timestamp()
    print "utc_str_timestamp():", current_utc_str_timestamp
    print " + de-serialized:", utc_timestamp2datetime(current_utc_str_timestamp)

if __name__ == '__main__':
    main()

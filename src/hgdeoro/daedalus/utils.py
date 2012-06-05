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

import time

from datetime import date

from pycassa.util import convert_uuid_to_time

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright (C) 2012 - Horacio Guillermo de Oro <hgdeoro@gmail.com>
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def ymd_from_epoch(a_time=None):
    """
    Returns a string with the format YEAR+MONTH+DAY.
    If 'a_time' is None (default) generates YMD for now.
    """
    if a_time is None:
        a_time = time.time()
    a_date = date.fromtimestamp(a_time)
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)


def ymd_from_uuid1(uuid1_value):
    """
    Returns a string with the format YEAR+MONTH+DAY
    """
    a_date = date.fromtimestamp(convert_uuid_to_time(uuid1_value))
    return "{0:04d}{1:02d}{2:02d}".format(
        a_date.year, a_date.month, a_date.day)

#-------------------------------------------------------------------------------
# Name:        Sniv
# Purpose:     Track unavailability of squadron assets
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from datetime import date, datetime, time, timedelta


class Sniv(object):
    """This is the sniv class"""

    def __init__(self, *initial_data, **kwargs):
        self.start = datetime.now()
        self.end = datetime.now()
        self.sniv_ID = None
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.begin = self.start

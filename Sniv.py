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

    def __init__(self):
        self.begin = datetime.now()
        self.end = datetime.now()

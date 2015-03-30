#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
from Event import Event
from Sniv import Sniv
from Wave import Wave
from Resource import Resource
from Flyer import Flyer
from Plane import Plane
from datetime import date, datetime, time, timedelta


def main():
    s = Sniv()
    s.begin = datetime(2015,3,28,8)
    s.end = datetime(2015,3,28,9,30)
    w = Wave()
    w.begin=datetime(2015,3,28,10)
    w.end = datetime(2015,3,28,12,30)
    w.times["Flyer"].begin = datetime(2015,3,28,9)
    w.times["Flyer"].end = datetime(2015,3,28,13,30)
    w.times["Plane"].begin = datetime(2015,3,28,10)
    w.times["Plane"].end = datetime(2015,3,28,12,30)
    r = Flyer(1)
    r.snivs[0]=s
    print "Flyer"
    print r.available(date(2015,3,28),w)
    print r._available[date(2015,3,28)][w]

    print "Plane"
    p = Plane(1)
    p.snivs[0]=s
    print p.available(date(2015,3,28),w)
    print p._available[date(2015,3,28)][w]

if __name__ == '__main__':
    main()

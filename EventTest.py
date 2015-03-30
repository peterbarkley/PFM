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

from Sniv import Sniv
from Wave import Wave
from Resource import Resource
from datetime import date, datetime, time, timedelta
from Squadron import Squadron
from Schedule import Schedule
from Sniv import Sniv
from Flyer import Flyer
from Instructor import Instructor
from Student import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Plane import Plane

def main():
    vtna=Squadron()
    dates = [date(2015,3,27),date(2015,3,28)] #Dates to write schedules for. Should be passed via sys.argv Assume unlisted gap dates are blank schedules.
    #Dealing with blank schedules needs more work. Schedules need to know if crew rests constraints apply from the previous day
    i=1
    for day in dates:
        sked=Schedule(day)
        sked.flyDay = i
        sked.waves[1].first = True
        vtna.schedules[day]=sked
        i=i+1

    #Creates the events in the syllabus. Would be replaced by call to data if necessary.
    for i in range(-3,11):
        e = Event(i)
        if i > -3:
            vtna.syllabus[i-1].followingEvents.add(e)
        if i>0:
            e.flightHours=1.0
            if i != 5 and i !=9:
                e.onwing=True
        vtna.syllabus[i]=e

    vtna.syllabus[-3].initialEvent = True
    vtna.syllabus[5].offwing=True
    vtna.syllabus[9].offwing=True
    vtna.syllabus[9].check=True
    vtna.syllabus[10].followsImmediately=True

    s = Student("Test",vtna)
    d =date(2015,3,27)
    for k in s.events(d,vtna.schedules[d].waves[1]):
        print d, 1
        print k
    d =date(2015,3,28)
    for k in s.events(d,vtna.schedules[d].waves[1]):
        print d, 1
        print k
    for k in s.events(d,vtna.schedules[d].waves[2]):
        print d, 2
        print k

if __name__ == '__main__':
    main()

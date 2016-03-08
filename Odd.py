#-------------------------------------------------------------------------------
# Name:        Student
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from Flyer import Flyer
from datetime import timedelta
from datetime import datetime


class Student(Flyer):
    """Student implementation of Flyer class. Adds a next event, onwing, partner, priority"""

    def __init__(self, *initial_data, **kwargs):
        # self.student_ID = None
        self.nextEvent = None
        self.onwing = None #Instructor object
        self.partner = None #Student object
        self.priority = None
        self.lastFlight = None
        self.syllabus = None
        self.resourceType = "Student"
        self.completedEvents = set() # set of events objects for each completed event
        self.scheduledEvents = set() # set of events objects for each currently scheduled event
        self._possibleEvents = {}
        super(Student, self).__init__(*initial_data, **kwargs)
        # self.id = self.student_ID

    #Should take in the number of flight days in the future that the events are possible
    #Returns the events the student can be feasibly scheduled for on that day
    #Recursively finds the events that could be done on a day 'flyDay' days in the future in a wave that is 'first' or not
    def findPossible(self,flyDay,first):
        if (flyDay,first) in self._possibleEvents:
            return self._possibleEvents[(flyDay,first)]
        elif not first:
            possible=self.findPossible(flyDay,True)
            newlyPossible = set()
            for e in possible:
                for f in e.followingEvents:
                    if f.followsImmediately:
                        newlyPossible.add(f)
            possible = possible|newlyPossible
            self._possibleEvents[(flyDay,first)]=possible
            return possible
        elif flyDay > 1:
            possible=self.findPossible(flyDay-1,False)
            newlyPossible = set()
            for e in possible:
                for f in e.followingEvents:
                    newlyPossible.add(f)
            possible = possible|newlyPossible
            self._possibleEvents[(flyDay,first)]=possible
            return possible
        else:
            #First wave, first day, not in dictionary
            possible=set()
            for e in self.squadron.syllabus:
                event = self.squadron.syllabus[e]
                if event.syllabus == self.syllabus and event.initialEvent():
                    possible.add(event)
            for e in self.completedEvents | self.scheduledEvents:
                for f in e.followingEvents:
                    possible.add(f)
            for e in self.completedEvents | self.scheduledEvents:
                if e in possible:
                    possible.remove(e)
            self._possibleEvents[(flyDay,first)]=possible
            return possible

    #Returns a set of events that would be possible on 'day' in 'wave'
    def events(self,day,wave):
        first = wave.first()
        return self.findPossible(day,first)


    def getPriority(self):
        if self.priority == None:
            e = self.getNextEvent()
            if e.id != 10:
                p = 2*(10-e.id)
            else:
                p = 20
            days = 0
            if self.lastFlight != None:
                interval = datetime.combine(self.squadron.schedules[1].date,datetime.min.time()) - self.lastFlight
                d = interval.days + interval.seconds/(24*3600)
                if d>=2:
                    p += 2
                if d>=3:
                    p += 5 + d
            self.priority = p/2.0
        return self.priority

    def getNextEvent(self):
        if self.nextEvent == None and self.findPossible(1,True):
            self.nextEvent = min(self.findPossible(1,True))
        return self.nextEvent


def main():
    pass

if __name__ == '__main__':
    main()

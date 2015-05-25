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
from sets import Set
class Student(Flyer):
    """Student implementation of Flyer class. Adds a next event, onwing, partner, priority"""

    def __init__(self, id, squadron):
        super(Student, self).__init__(id)
        self.squadron = squadron
        self.nextEvent = None
        self.onwing = None #Instructor object
        self.partner = None #Student object
        self.priority = 1
        self.syllabus = None
        self.resourceType = "Student"
        self.crewRest = timedelta(hours=12)
        self.completedEvents = Set() #Set of events objects for each completed event
        self.scheduledEvents = Set() #Set of events objects for each currently scheduled event
        self._possibleEvents = {}

    #Should take in the number of flight days in the future that the events are possible
    #Returns the events the student can be feasibly scheduled for on that day
    #Recursively finds the events that could be done on a day 'flyDay' days in the future in a wave that is 'first' or not
    def findPossible(self,flyDay,first):
        if (flyDay,first) in self._possibleEvents:
            return self._possibleEvents[(flyDay,first)]
        elif not first:
            possible=self.findPossible(flyDay,True)
            newlyPossible = Set()
            for e in possible:
                for f in e.followingEvents:
                    if f.followsImmediately:
                        newlyPossible.add(f)
            possible = possible|newlyPossible
            self._possibleEvents[(flyDay,first)]=possible
            return possible
        elif flyDay > 1:
            possible=self.findPossible(flyDay-1,False)
            newlyPossible = Set()
            for e in possible:
                for f in e.followingEvents:
                    newlyPossible.add(f)
            possible = possible|newlyPossible
            self._possibleEvents[(flyDay,first)]=possible
            return possible
        else:
            #First wave, first day, not in dictionary
            possible=Set()
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

    #Returns a Set of events that would be possible on 'day' in 'wave'
    def events(self,day,wave):
        first = wave.first()
        return self.findPossible(day,first)





def main():
    pass

if __name__ == '__main__':
    main()

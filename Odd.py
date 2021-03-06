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

from gurobipy import tuplelist
from Flyer import Flyer
from datetime import datetime, date, timedelta


class Student(Flyer):
    """Student implementation of Flyer class. Adds a next event, onwing, partner, priority"""

    def __init__(self, *initial_data, **kwargs):
        # self.student_ID = None
        self.nextEvent = None
        self.onwing = None #Instructor object
        self.partner = None #Student object
        self.priority = None
        self.last_flight = None
        self.syllabus = set() # Dict of syllabus objects the student is enrolled in
        self.completedEvents = set() # set of events objects for each completed event
        self.scheduledEvents = set() # set of events objects for each currently scheduled event
        self.progressing = set()  # Set of (event object, syllabus object) tuples that do not need to be scheduled
        self._possibleEvents = {}
        self.onwing_instructor_ID = None
        self.partner_student_ID = None
        self.student_syllabus_ID = None  # Future Work: this should be across all syllabi
        self.probability = 0.8  # Probability of a single event being successful
        self.training_end_date = None  # Date when training should be finished
        super(Student, self).__init__(*initial_data, **kwargs)
        self.resourceType = "Student"
        if self.id is None:
            self.id = self.student_ID

    #Should take in the number of flight days in the future that the events are possible
    #Returns the events the student can be feasibly scheduled for on that day
    #Recursively finds the events that could be done on a day 'flyDay' days in the future in a wave that is 'first' or not
    def findPossible(self, flyDay, first):
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

    # Returns a set of events that would be possible on integer flight day 'day' in wave object 'wave'
    def events(self, day, wave):
        first = wave.first()
        return self.findPossible(day, first)


    def getPriority(self):
        if self.priority is None:
            e = self.getNextEvent()
            if e.id != 10:
                p = 2*(10-e.id)
            else:
                p = 20
            days = 0
            if self.last_flight != None:
                interval = datetime.combine(self.squadron.schedules[1].date,datetime.min.time()) - self.last_flight
                d = interval.days + interval.seconds/(24*3600)
                if d >= 2:
                    p += 2
                if d >= 3:
                    p += 5 + d
            self.priority = p/2.0
        return self.priority

    def countRemainingEvents(self):
        # Count remaining events
        remaining_events = set()
        for syllabus in self.syllabus:
            remaining_events = (set([(e, syllabus) for e in syllabus.events.values()]) - self.progressing) | remaining_events
        return len(remaining_events)

    def getBetterPri(self):
        # Find days remaining
        remaining_days = self.training_end_date - date.today()
        event_priority = 1.01**(self.countRemainingEvents() - remaining_days.days)
        self.priority = event_priority
        if self.last_flight is not None:
            recency = date.today() - self.last_flight
            recency_bonus = recency.days/3
            self.priority += recency_bonus
        return self.priority


    def getNextEvent(self):
        if self.nextEvent is None and self.findPossible(1, True):
            self.nextEvent = min(self.findPossible(1, True))
        return self.nextEvent

    def getOnwing(self):
        if self.onwing is not None:
            return self.onwing
        else:
            return self.squadron.instructors.get(self.onwing_instructor_ID)

    def getPartner(self):
        if self.partner is not None:
            return self.partner
        else:
            return self.squadron.students.get(self.partner_student_ID)

    # Takes an integer level and returns the (event, syllabus) tuples
    # that could be scheduled at that tier given precedence constraints
    def event_tier(self, level):
        tier = set()
        if level > 0:
            previous_tier = self.event_tier(level - 1)
        else:
            previous_tier = set()
        for s in self.syllabus:
            old_events = self.progressing | previous_tier
            new_events = set([(e, s) for e in s.events.values()]) - old_events
            higher_priority_events = set()
            """for t in self.syllabus:
                if t.precedence > s.precedence:
                    higher_priority_events += set(t.events.keys())
            """
            ungraded = set()
            for e, syllabus in new_events:
                parents = s.parents(e) | higher_priority_events
                if parents <= old_events:
                    tier.add((e, s))
                elif not e.graded:
                    ungraded.add(e)
            for e in ungraded:
                if (s.ancestors(e) | higher_priority_events) <= (old_events | tier | ungraded):
                    tier.add((e, s))

        return tier | previous_tier


def main():
    pass

if __name__ == '__main__':
    main()

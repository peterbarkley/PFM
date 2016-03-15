#-------------------------------------------------------------------------------
# Name:        Event
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
from datetime import timedelta

class Event(object):
    """Implements the events class"""

    def __init__(self, *initial_data, **kwargs):
        self.id = None # Event ID
        self.event_ID = None
        self.name = None
        self.device_category = None
        self.ground_instruction_hours = 0
        self.ground_device_hours = 0
        self.dual_flight_hours = 0
        self.solo_flight_hours = 0
        self.stage = None
        self.media = None
        self.description = "I am a poor, unloved event"
        self.onwing = False # Onwing required
        self.offwing = False # Offwing required
        self.flightHours = 0.0 # Number of flight hours obligated by this event
        self.instructionalHours = 1.0 # Number of additional instructor hours
        self.planeHours = 0.0 # Number of dedicated plane hours required
        self.brief_hours = 0.5
        self.debrief_hours = 0.5
        self.check = False # Whether this requires a check pilot
        self.prereqs = []
        self.max_students = 2
        self.followsImmediately = False
        self.followingEvents = set() # Gives the events that this is a prerequisite for
        self.precedingEvents = set() # Gives the events that are a prerequisite for this one
        self.syllabus = 1
        self.rules = []
        self.graded = True
        self.constraints = []
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self.id = self.event_ID

    def __str__(self):
        return "Event_" + str(self.id)

    def flight(self):
        return self.flightHours > 0

    def getDebriefHours(self):
        return timedelta(hours=self.debrief_hours)

    #Returns true if this event has no prerequisites and can be scheduled without any previous events completed
    def initialEvent(self):
        return len(self.precedingEvents) == 0

    def deviceHours(self):
        return float(self.dual_flight_hours + self.solo_flight_hours + self.ground_device_hours)

def main():
    pass

if __name__ == '__main__':
    main()

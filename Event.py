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

from sets import Set

class Event(object):
    """Implements the events class"""

    def __init__(self,id):
        self.id = id #Event ID
        self.onwing = False #Onwing required
        self.offwing = False #Offwing required
        self.flightHours = None #Number of flight hours obligated by this event
        self.planeHours = None #Number of dedicated plane hours required
        self.check = False #Whether this requires a check pilot
        self.prereqs = []
        self.maxStudents = 2
        self.followsImmediately = False
        self.followingEvents = Set() #Gives the events that this is a prerequisite for
        self.precedingEvents = Set()
        self.initialEvent = False

    def __str__(self):
        return "Event "+str(self.id)

    def flight(self):
        return self.flightHours > 0


def main():
    pass

if __name__ == '__main__':
    main()

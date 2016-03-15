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
#from Schedule import Schedule
from datetime import timedelta


class Wave(object):

    def __init__(self, id):
        self.id = id
        self.begin = None #a datetime giving the date and time for the start of the wave
        self.end = None
        self.priority = 1.0
        self.times = {}
        self.times["Plane"] = Sniv()
        self.times["Flyer"] = Sniv()
        self.times["Student"] = self.times["Flyer"]
        self.times["Instructor"] = self.times["Flyer"]
        self.studentMultiple = 1 #Allows double or triple waves
        self.schedule = None
        self._canFollow = []
        """ self._canFollow includes itself, so for an out-and-in the student can have
                                  sequential events that can follow immediately both in the same wave"""
        self._canFollowCalculated = False
        self.crewRestHours = 12 #Max time between first brief and last debrief
        self.tags = set()
        self._tier = None

    def __str__(self):
        return "Wave_" + str(self.id)

    # Returns the set of waves that a student could be scheduled for and still make this one
    def canImmediatelyFollow(self):
        sked = self.schedule
        if sked != None and not self._canFollowCalculated:
            for w in sked.waves:
                wave = sked.waves[w]
                if (wave.times["Flyer"].end <= self.times["Flyer"].begin):
                    self._canFollow.append(w)
            self._canFollowCalculated = True
        return self._canFollow

    def first(self):
        self.canImmediatelyFollow()
        if len(self._canFollow) > 0:
            return False
        else:
            return True

    def planeHours(self):
        diff = self.times["Plane"].end - self.times["Plane"].begin
        fudge = 0
        h = diff.seconds/3600.0
        """if h >= 2.0:
            fudge = 0.2"""
        return h - fudge

    # Future work: fix canImmediatelyFollow to return min(tier + 1) across any events it can follow else 0
    def tier(self):
        if self._tier is None:
            possible_tiers = []
            for w in self.schedule.waves.values():
                if w.times["Flyer"].end <= self.times["Flyer"].begin:
                    possible_tiers.append(w.tier() + 1)
            if possible_tiers:
                self._tier = min(possible_tiers)
            else:
                self._tier = 0
        return self._tier



def main():
    pass

if __name__ == '__main__':
    main()

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

    def __init__(self,id):
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
        self._canFollow = [id] #This includes itself, so for an out-and-in the student can have sequential events that can follow immediately both in the same wave
        self._canFollowCalculated = False
        self.crewRestHours = 12 #Max time between first brief and last debrief

    def __str__(self):
        return "wave"+str(self.id)

    def canImmediatelyFollow(self):
        sked = self.schedule
        if sked != None and not self._canFollowCalculated:
            for w in sked.waves:
                wave = sked.waves[w]
                if  wave.times["Flyer"].end <= self.times["Flyer"].begin and self.times["Flyer"].end - wave.times["Flyer"].begin < timedelta(hours=self.crewRestHours):
                    self._canFollow.append(w)
            self._canFollowCalculated = True
        return self._canFollow

    def first(self):
        self.canImmediatelyFollow()
        if len(self._canFollow)>1:
            return False
        else:
            return True






def main():
    pass

if __name__ == '__main__':
    main()

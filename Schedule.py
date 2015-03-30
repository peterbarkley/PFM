#-------------------------------------------------------------------------------
# Name:        Schedule
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from datetime import date, datetime, time, timedelta
from Wave import Wave
from Resource import Resource
from Plane import Plane
from Flyer import Flyer

class Schedule(object):
    """Contains all information necessary for structuring a day's schedule.
    Once a schedule is written, holds a list of the sorties in the schedule."""
    def __init__(self,d):
        self.sorties=[]
        self.backToBack = True #Whether instructors may fly back to back sorties with no break
        self.firstBrief = time(6,30) #Time of first brief
        self.briefLength = timedelta(hours=1)
        self.staggers = {} #A dictionary of staggered timedeltas for sorties like {'1':timedelta(minutes=5),'2':timedelta(minutes=7)}
        self.date = d #A date object giving the date of the schedule to be
        self.waveLength = timedelta(hours=2.5)
        self.waveNumber = 5
        self.crewRest = False #Whether to build in crew rest constraints (more work: for previous day or subsequent?)
        self.priority = 1 #Sets the weight of an event scheduled this day
        self.waves = {}
        self.exclusiveWaves = {}
        self.exclusiveWaves["Flyer"]=[]
        self.exclusiveWaves["Plane"]=[]
        self.createWaves()
        self.maxStudents = 2 #Sets the max students for a sortie
        self.blank = False #Sets whether a schedule should contain no events
        self.flyDay = 1

    def createWaves(self):
        self.waves = {}
        _begin = datetime.combine(self.date,self.firstBrief) + self.briefLength
        for i in range(1,self.waveNumber+1):
            _end = _begin + self.waveLength
            w=Wave(i)
            w.begin = _begin
            w.end = _end
            w.times["Flyer"].begin = _begin - self.briefLength
            w.times["Flyer"].end = _end + self.briefLength
            w.times["Plane"].begin = _begin
            w.times["Plane"].end = _end
            self.waves[i]=w
            _begin = _end

            #Determine whether flying wave i excludes wave j for each resource type
            for j in range(1,i):
                f = Flyer('sample')
                f.snivs[0]=self.waves[j].times["Flyer"]
                if not f.available(self.date,self.waves[i]):
                    self.exclusiveWaves["Flyer"].append((j,i))
                f = Plane('sample')
                f.snivs[0]=self.waves[j].times["Plane"]
                if not f.available(self.date,self.waves[i]):
                    self.exclusiveWaves["Plane"].append((j,i))

    def setWaveNumber(self,wn):
        self.waveNumber = wn
        createWaves(self)




def main():
    pass

if __name__ == '__main__':
    main()

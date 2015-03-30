#-------------------------------------------------------------------------------
# Name:        Flyer
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
from Resource import Resource
from datetime import timedelta

class Flyer(Resource):
    """This is the base class for instructors and students"""

    def __init__(self,id):
        super(Flyer, self).__init__(id)
        self.quals = []
        self.last = {'wave':None,'plane':None}
        self.weight = None
        self.priority = 1
        self.resourceType = "Flyer"
        self.crewRest = timedelta(hours=8)

    #Returns true if the schedule should begin with this Flyer scheduled during 'wave' in 'plane'
    def seed(self,wave,plane):
        if(self.last['wave']==wave and self.last['plane']==plane):
            return True
        else:
            return False

    #Might want setSeed(self,wave,plane) function so user doesn't mess with data structure

    #Might want setQual(self,planetype) which appends a planetype string to self.quals

    #Might want getQual(self,planetype) returns true if planetype in quals
    def qualified(self,planetype):
        return planetype in self.quals


def main():
    pass

if __name__ == "__main__":
    main()
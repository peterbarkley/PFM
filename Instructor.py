#-------------------------------------------------------------------------------
# Name:        Instructor
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------


from Flyer import Flyer

class Instructor(Flyer):
    """Instructor implementation of Flyer class. Adds a check pilot boolean"""

    def __init__(self, id):
        super(Instructor, self).__init__(id)
        self.check = False
        self.priority = -0.1 #Needs to be negative. This encourages the model to schedule the minimum number of instructors
        self.maxEvents = 3
        self.preferences = {} #1 is a high preference, 5 is a low preference
        self.resourceType = "Instructor"

    def setPreference(self,day,wave,amount):
        self.preferences[(day,wave)]=amount

    def getPreference(self,day,wave):
        if (day,wave) in self.preferences:
            return self.priority*self.preferences[(day,wave)]
        else:
            return 3*self.priority


def main():
    pass

if __name__ == '__main__':
    main()

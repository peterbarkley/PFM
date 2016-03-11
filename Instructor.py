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

    def __init__(self, *initial_data, **kwargs):
        self.check = False
        self.priority = -0.1 #Needs to be negative. This encourages the model to schedule the minimum number of instructors
        self.max_events = 4
        self.preferences = {} #1 is a high preference, 5 is a low preference
        self.paid = 0
        self.instructor_ID = None
        super(Instructor, self).__init__(*initial_data, **kwargs)
        self.resourceType = "Instructor"
        if self.id is None:
            self.id = self.instructor_ID

    def setPreference(self,d,w,amount):
        self.preferences[(d,w)]=amount

    def getPreference(self,d,w):
        pri = self.priority
        #if not self.paid:
        #    pri = pri/10
        if (d,w) in self.preferences:
            return pri*self.preferences[(d,w)]
        else:
            return 3*pri


def main():
    pass

if __name__ == '__main__':
    main()

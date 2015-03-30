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

class Wave(object):

    def __init__(self,id):
        self.id = id
        self.begin = None #a datetime giving the date and time for the start of the wave
        self.end = None
        self.priority = 1
        self.times = {}
        self.times["Plane"] = Sniv()
        self.times["Flyer"] = Sniv()
        self.times["Student"] = self.times["Flyer"]
        self.times["Instructor"] = self.times["Flyer"]
        self.studentMultiple = 1 #Allows double or triple waves
        self.first = False

    def __str__(self):
        return "wave"+str(self.id)

def main():
    pass

if __name__ == '__main__':
    main()

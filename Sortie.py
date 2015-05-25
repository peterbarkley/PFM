#-------------------------------------------------------------------------------
# Name:        Sortie
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

class Sortie(object):
    """Implements a sortie in an aircraft.
    This implies a single brief time and a single instructor, as well as a time to get and relinquish an aircraft.
    It also has student Sorties associated with it"""
    def __init__(self):
        self.brief = None
        self.instructor = None #Instructor object
        self.studentSorties = []
        self.takeoff = None
        self.land = None
        self.plane = None #Plane object
        self.wave = None #Wave ojbect

def main():
    pass

if __name__ == '__main__':
    main()

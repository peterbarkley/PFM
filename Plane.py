#-------------------------------------------------------------------------------
# Name:        Plane
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
from Resource import Resource

class Plane(Resource):
    """Plane class"""
    def __init__(self,id):
        super(Plane, self).__init__(id)
        self.planetype = None
        self.maxWeight = 650
        self.stagger = 0 #Id of the stagger value from the start of the wave for this aircraft
        self.resourceType = "Plane"


def main():
    pass

if __name__ == '__main__':
    main()

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
import decimal

class Plane(Resource):
    """Plane class"""
    def __init__(self, *initial_data, **kwargs):
        self.planetype = None
        self.maxWeight = 650
        self.stagger = 0 #Id of the stagger value from the start of the wave for this aircraft
        self.resourceType = "Plane"
        self.hours = 100.0
        self.priority = 0 #1-5, 1 is high pri, 5 is low pri
        self.target = {} #Dictionary of target flight hours for each flyday {1: 12.5 2: 5.0 3:12.5}
        super(Plane, self).__init__(*initial_data, **kwargs)


def main():
    pass

if __name__ == '__main__':
    main()

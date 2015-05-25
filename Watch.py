#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      pbarkley
#
# Created:     14/05/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
from Sniv import Sniv

class Watch(object):

    def __init__(self,id):
        self.id = id #Watch ID
        self.name = None
        self.periods = {} #Like {watch_period_ID: Sniv()}

def main():
    pass

if __name__ == '__main__':
    main()

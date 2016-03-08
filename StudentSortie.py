#-------------------------------------------------------------------------------
# Name:        Student Sortie
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

class StudentSortie(object):
    """Represents a scheduled event for a student. Has an event associated with it and a student"""
    def __init__(self, student = None, event = None):
        self.student = student # Student object
        self.event = event
        self.wave = None

    def __str__(self):
        return str(self.student) + '\t' + str(self.event)
def main():
    pass

if __name__ == '__main__':
    main()

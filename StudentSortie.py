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
    def __init__(self, *initial_data, **kwargs):
        self.student = None # Student object
        self.event = None
        self.wave = None
        self.student_sortie_ID = None
        self.student_syllabus_ID = None
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __str__(self):
        return str(self.student) + '_' + str(self.event)
def main():
    pass

if __name__ == '__main__':
    main()

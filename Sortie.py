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
from Qual import Qual
from copy import copy

class Sortie(object):
    """Implements a sortie in an aircraft.
    This implies a single brief time and a single instructor, as well as a time to get and relinquish an aircraft.
    It also has student Sorties associated with it"""
    def __init__(self, instructor = None, plane = None):
        self.brief = None
        self.instructor = instructor #Instructor object
        self.studentSorties = []
        self.takeoff = None
        self.land = None
        self.plane = plane #Plane object
        self.planeType = None
        self.wave = None #Wave ojbect
        self.schedule_ID = None

    def __str__(self):
        header = str(self.brief) + '\t' + str(self.takeoff) + '\t' + str(self.land) + '\t' + str(self.plane)
        output = ''
        if self.studentSorties:
            for ss in self.studentSorties:
                output = output + header + '\t' + str(self.instructor) + '\t' + str(ss) + '\n'

            return output

        return header + '\t' + str(self.instructor) + '\n'

    def getDict(self,studentSortie):
        d = studentSortie.__dict__
        # d['student'] = d['student'].id
        # d['event'] = d['event'].id
        d['plane'] = self.plane
        d['instructor'] = self.instructor
        return d

    def export(self):
        return {'brief': self.brief,
             'scheduled_takeoff': self.takeoff,
             'scheduled_land': self.land,
             'instructor_ID': self.instructor.instructor_ID,
             'schedule_ID': self.schedule_ID,
             'wave_ID': self.wave.id
            }

    def feasible(self):

        feasibility = True
        # Check instructor rules
        if self.planeType and self.instructor:
            q = Qual(self.planeType)
            """print q
            for qq in self.instructor.quals:
                print qq"""
            feasibility = feasibility and (q in self.instructor.quals)
            """if not feasibility:
                print "Instructor Planetype"""""

        if self.planeType and self.plane:
            """print self.plane.planetype
            print self.planeType"""
            feasibility = feasibility and (self.plane.planetype == self.planeType)
            """if not feasibility:
                print "Plane Planetype"""""

        for studentSortie in self.studentSorties:
            for rule in studentSortie.event.rules:
                if self.instructor and rule.subject == 'instructor':
                    q = copy(rule.qual)
                    if q.objectType and not q.object:
                        q.bind(self.getDict(studentSortie))
                    """print q.__dict__
                    for qq in self.instructor.quals:
                        print qq.__dict__"""
                    feasibility = feasibility and ((q in self.instructor.quals) == rule.positive)
                    """if not feasibility:
                        print rule"""
            if self.planeType:
                feasibility = feasibility and (Qual(self.planeType) in studentSortie.student.quals)
                """print self.planeType
                for q in studentSortie.student.quals:
                    print q
                if not feasibility:
                    print 'Student Planetype'"""

        return feasibility

def main():
    pass

if __name__ == '__main__':
    main()

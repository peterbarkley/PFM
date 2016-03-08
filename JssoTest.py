import unittest
from JSSO import JobShop
from Rule import Rule
from Instructor import Instructor
from Student import Student
from Event import Event
from Plane import Plane
from Schedule import Schedule
from Sortie import Sortie
from StudentSortie import StudentSortie
from Squadron import Squadron
from Qual import Qual
from datetime import *
from Sniv import Sniv


class JssoTestCase(unittest.TestCase):

    def event_setup(self, squadron, count):
        r = Rule('onwing')
        r.subject = 'instructor'
        r.qual = Qual('onwing')
        r.qual.objectType = 'student'
        for i in range(1, count + 1):
            e = Event(i)
            e.flightHours = 1.0
            e.instructionalHours = 0.0
            e.rules.append(r)
            if i-1 in squadron.syllabus:
                e.precedingEvents.add(squadron.syllabus[i-1])
                squadron.syllabus[i-1].followingEvents.add(e)
            squadron.syllabus[i] = e

    def student_setup(self, squadron, count, instructors):
        for i in range(1, count + 1):
            st = Student(i, squadron)
            st.quals.append(Qual('C-172'))
            st.syllabus = 1
            # st.onwing = squadron.instructors[i % instructors]
            squadron.students[i] = st
        s = Sniv()
        s.begin = datetime(2016, 2, 13, hour=7)
        s.begin = datetime(2016, 2, 13, hour=9)
        squadron.students[1].snivs[1] = s

    def instructor_setup(self, squadron, count):
        for i in range(-count, 0):
            squadron.instructors[i] = Instructor(i)
            squadron.instructors[i].quals.append(Qual('C-172'))

    def plane_setup(self, squadron, count):
        for i in range(1, count + 1):
            squadron.planes[i] = Plane(i)
            squadron.planes[i].planetype = 'C-172'

    def jsso_setup(self, vt):
        # vt = JobShop()
        # vt.verbose = False
        d = date(2016,2,13)
        for i in range(1, 3):
            vt.schedules[i] = Schedule(d + timedelta(days = i))
            if not i % 7:
                vt.schedules[i].blank = True
        instructors = 10
        self.event_setup(vt, 2)
        self.student_setup(vt, 85, instructors)
        self.instructor_setup(vt, instructors)
        self.plane_setup(vt, 11)
        for s, stud in vt.students.iteritems():
            i = -instructors + (s % instructors)
            q = Qual('onwing')
            q.objectType = 'student'
            q.object = stud
            vt.instructors[i].quals.append(q)
        return vt

    def test_jobshop(self):
        vt = self.jsso_setup(JobShop())
        print vt.instructors
        self.assertTrue(vt.writeSchedules())


if __name__ == '__main__':
    unittest.main()

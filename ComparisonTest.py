import unittest
from Squadron import Squadron
from Wave import Wave
from datetime import *
from Schedule import Schedule
from Instructor import Instructor
from Student import Student
from Event import Event
from Plane import Plane
from Qual import Qual


class ComparisonTest(unittest.TestCase):

    def create_waves(self, sked):
        for i in range(1, 6):
            w = Wave(i)
            #Plane times
            dawn = datetime.combine(sked.date, sked.dawn)
            start_time = dawn + timedelta(hours=(i-1)*2.5)
            end_time = dawn + timedelta(hours=i*2.5)
            w.begin = start_time
            w.end = end_time
            w.times["Plane"].begin = start_time
            w.times["Plane"].end = end_time
            #Flyer times
            start_time = start_time - timedelta(hours=1)
            end_time = start_time - timedelta(hours=1)
            w.times["Flyer"].begin = start_time
            w.times["Flyer"].end = end_time
            w.schedule = sked
            w.priority = 1.0
            sked.waves[i]=w
        sked.findExclusiveWaves()

    def event_setup(self, squadron, count):
        for i in range(1, count + 1):
            squadron.syllabus[i] = Event(i)
            squadron.syllabus[i].flightHours = 1.0
            squadron.syllabus[i].instructionalHours = 0.0
            if i-1 in squadron.syllabus:
                squadron.syllabus[i].precedingEvents.add(squadron.syllabus[i-1])
                squadron.syllabus[i-1].followingEvents.add(squadron.syllabus[i])

    def student_setup(self, squadron, count):
        for i in range(1, count + 1):
            squadron.students[i] = Student(i, squadron)
            squadron.students[i].quals.append(Qual('C-172'))
            squadron.students[i].syllabus = 1

    def instructor_setup(self, squadron, count):
        for i in range(-count,0):
            squadron.instructors[i] = Instructor(i)
            squadron.instructors[i].quals.append(Qual('C-172'))

    def plane_setup(self, squadron, count):
        for i in range(1, count + 1):
            squadron.planes[i] = Plane(i)
            squadron.planes[i].planetype = 'C-172'

    def pfm_setup(self, vt):
        # vt = JobShop()
        vt.verbose = False
        d = date(2016,2,13)
        for i in range(1, 17):
            vt.schedules[i] = Schedule(d + timedelta(days = i))
            if not i % 7:
                vt.schedules[i].blank = True
            else:
                self.create_waves(vt.schedules[i])
        self.event_setup(vt,4)
        self.student_setup(vt,2)
        self.instructor_setup(vt,1)
        self.plane_setup(vt,1)
        return vt

    def test_pfm(self):
        vt = self.pfm_setup(Squadron())
        vt.writeSchedules()
        total = 0
        for key, var in vt.sevents.iteritems():
            if var.x:
                total += 1
        print 'PFM Total:', total
        # js_vt = JssoTestCase.jsso_setup(JobShop())
        self.assertTrue(total) # == js_vt.writeSchedules())


if __name__ == '__main__':
    unittest.main()

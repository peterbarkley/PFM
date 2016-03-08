import unittest
from Rule import Rule
from Instructor import Instructor
from Student import Student
from Event import Event
from Plane import Plane
from Sortie import Sortie
from StudentSortie import StudentSortie
from Squadron import Squadron
from Qual import Qual


class RuleTest(unittest.TestCase):

    def setUp(self):
        i = Instructor(1)
        squad = Squadron()
        stud = Student(2, squad)
        q = Qual('C-172')
        stud.quals.append(q)
        e = Event(1)
        r = Rule('onwing')
        e.rules.append(r)
        ss = StudentSortie()
        ss.student = stud
        ss.event = e
        sor = Sortie()
        sor.studentSorties.append(ss)
        sor.instructor = i
        return sor

    def plane_setup(self):
        sor = self.setUp()
        sor.planeType = 'C-172'
        return sor

    def test_check_true(self):
        sor = self.setUp()
        check = Qual('Check')
        sor.instructor.quals.append(check)
        ss = sor.studentSorties[0]
        r = ss.event.rules[0]
        r.subject = 'instructor'
        r.qual = Qual('Check')
        self.assertTrue(sor.feasible())

    def test_check_false(self):
        sor = self.setUp()
        ss = sor.studentSorties[0]
        r = ss.event.rules[0]
        r.subject = 'instructor'
        r.qual = Qual('Check')
        self.assertFalse(sor.feasible())

    def onwing_setup(self):
        sor = self.setUp()
        ss = sor.studentSorties[0]
        r = ss.event.rules[0]
        r.subject = 'instructor'
        r.qual = Qual('Onwing')
        r.qual.objectType = 'student'
        return sor

    def test_onwing_true(self):
        sor = self.onwing_setup()
        q = Qual('Onwing')
        q.objectType = 'student'
        q.object = sor.studentSorties[0].student
        sor.instructor.quals.append(q)
        self.assertTrue(sor.feasible())

    def test_onwing_false(self):
        sor = self.onwing_setup()
        q = Qual('Check')
        sor.instructor.quals.append(q)
        self.assertFalse(sor.feasible())

    def not_onwing_setup(self):
        sor = self.setUp()
        ss = sor.studentSorties[0]
        r = ss.event.rules[0]
        r.subject = 'instructor'
        r.qual = Qual('Onwing')
        r.positive = False
        r.qual.objectType = 'student'
        return sor


    def test_not_onwing_false(self):
        sor = self.not_onwing_setup()
        q = Qual('Onwing')
        q.objectType = 'student'
        q.object = sor.studentSorties[0].student
        sor.instructor.quals.append(q)
        self.assertFalse(sor.feasible())


    def test_not_onwing_true(self):
        sor = self.not_onwing_setup()
        q = Qual('Check')
        sor.instructor.quals.append(q)
        self.assertTrue(sor.feasible())


    def test_instructor_planetype_true(self):
        sor = self.plane_setup()
        q = Qual('C-172')
        sor.instructor.quals.append(q)
        self.assertTrue(sor.feasible())


    def test_instructor_planetype_false(self):
        sor = self.plane_setup()
        q = Qual('PA-28')
        sor.instructor.quals.append(q)
        self.assertFalse(sor.feasible())


    def test_plane_planetype_true(self):
        sor = self.plane_setup()
        sor.instructor = None
        p = Plane('107LE')
        p.planetype = 'C-172'
        sor.plane = p
        sor.plane.planetype = 'C-172'
        self.assertTrue(sor.feasible())


    def test_plane_planetype_false(self):
        sor = self.plane_setup()
        sor.instructor = None
        p = Plane('107LE')
        p.planetype = 'PA-28'
        sor.plane = p
        # sor.plane.planetype = 'PA-28'
        self.assertFalse(sor.feasible())

if __name__ == '__main__':
    unittest.main()

import unittest
import vtSqlScheduler
import TrainingSquadron

template = {'instructor': None,
            'wave': None,
            'device': None,}

class HardscheduleTestCase(unittest.TestCase):




    def hardschedule_setup(self):
        # Build vt
        config = {}
        execfile('vt.conf', config)
        vt = TrainingSquadron.TrainingSquadron(config)
        vtSqlScheduler.load(vt, config)
        return vt

    def test_student_event_day(self):
        vt = self.hardschedule_setup()
        student = vt.students[9]
        event = vt.events[173]
        day = 2
        vt.schedules[day].hardschedule[(student, event)] = template
        vt.writeSchedules()
        total = 0
        for student, event, device, day, wave in vt.x.select(student, event, '*', day, '*'):
            total += vt.sevents[student, event, device, day, wave].x
        self.assertEqual(total, 1)

    def test_student_event_day_instructor(self):
        vt = self.hardschedule_setup()
        student = vt.students[9]
        event = vt.events[173]
        instructor = vt.instructors[18]
        instructor.priority = 2  # This makes the instructor less preferable
        day = 2
        t = {'instructor': instructor,
             'wave': None,
             'device': None,}
        vt.schedules[day].hardschedule[(student, event)] = t
        vt.writeSchedules()
        together = False
        for student, event, device, day, wave in vt.x.select(student, event, '*', day, '*'):
            if vt.sevents[student, event, device, day, wave].x and vt.ievents[instructor, device, day, wave].x:
                together = True
        self.assertTrue(together)

    def test_student_event_day_wave(self):
        vt = self.hardschedule_setup()
        student = vt.students[9]
        event = vt.events[173]
        day = 2
        schedule = vt.schedules[day]
        wave = schedule.waves[17]
        t = {'instructor': None,
             'wave': wave,
             'device': None,}
        schedule.hardschedule[(student, event)] = t
        vt.writeSchedules()
        together = False
        for student, event, device, day, wave in vt.x.select(student, event, '*', day, wave):
            if vt.sevents[student, event, device, day, wave].x:
                together = True
        self.assertTrue(together)

    """def test_student_event_day_instructor_wave(self):
        self.assertEqual(True, False)

    def test_student_event_day_instructor_wave_device(self):
        self.assertEqual(True, False)

    def test_student_event_day_instructor_device(self):
        self.assertEqual(True, False)

    def test_day_instructor_wave_device(self):
        self.assertEqual(True, False)

    def test_device_day(self):
        self.assertEqual(True, False)"""


if __name__ == '__main__':
    unittest.main()

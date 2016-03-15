import unittest
import Wave
import vtSqlScheduler
import TrainingSquadron
import Schedule
import datetime
from decimal import Decimal

class WaveTestCase(unittest.TestCase):
    def setUp(self):
        vt = TrainingSquadron.TrainingSquadron()
        s = Schedule.Schedule(schedule_ID=1)
        vt.schedules[1] = s
        waves = [{u'device_end': datetime.timedelta(0, 43200), u'flyer_end': datetime.timedelta(0, 45000),
                  u'flyer_start': datetime.timedelta(0, 20700), u'student_multiple': Decimal('2.00'), u'wave_ID': 1,
                  u'device_start': datetime.timedelta(0, 28800)},
                 {u'device_end': datetime.timedelta(0, 46800), u'flyer_end': datetime.timedelta(0, 48600),
                  u'flyer_start': datetime.timedelta(0, 24300), u'student_multiple': Decimal('2.00'), u'wave_ID': 2,
                  u'device_start': datetime.timedelta(0, 32400)},
                 {u'device_end': datetime.timedelta(0, 50400), u'flyer_end': datetime.timedelta(0, 52200),
                  u'flyer_start': datetime.timedelta(0, 27900), u'student_multiple': Decimal('2.00'), u'wave_ID': 3,
                  u'device_start': datetime.timedelta(0, 36000)}]
        wave_tags = {1: ['aircraft'],
                     2: ['aircraft'],
                     3: ['aircraft']}
        vtSqlScheduler.createWaves(vt, s, waves, wave_tags)
        return vt

    def test_wavetiers(self):
        vt = self.setUp()
        print vt.schedules[1].waves[1].times["Flyer"].begin
        print vt.schedules[1].waves[1].times["Flyer"].end
        print vt.schedules[1].waves[2].times["Flyer"].begin
        print vt.schedules[1].waves[2].times["Flyer"].end
        self.assertEqual(0, vt.schedules[1].waves[1].tier())
        self.assertEqual(0, vt.schedules[1].waves[2].tier())


if __name__ == '__main__':
    unittest.main()

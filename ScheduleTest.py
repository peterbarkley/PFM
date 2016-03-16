import unittest
import vtSqlScheduler
import TrainingSquadron


class ScheduleTestCase(unittest.TestCase):
    def schedule_setup(self):
        config = {}
        execfile('vt.conf', config)
        vt = TrainingSquadron.TrainingSquadron(config)
        vtSqlScheduler.load(vt, config)
        return vt

    def test_crewrest(self):
        vt = self.schedule_setup()
        s = vt.schedules[1]
        t = vt.schedules[2]
        for wave1, wave2 in vt.crewrest_pairs(1, "Student"):
            print wave1, wave2
        self.assertTrue((s.waves[17], t.waves[14]) in vt.crewrest_pairs(1, "Student"))


if __name__ == '__main__':
    unittest.main()

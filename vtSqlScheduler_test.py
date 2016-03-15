import unittest
import mysql.connector
import sys


class VtDatabaseTestCase(unittest.TestCase):

    # Load vt(1).sql into vt_test database
    # Run vtSqlScheduler.py with vt.conf
    # Check syllabi
    #    Check Syllabi
    #   Check Schedules
    #    Check Forecast
    #    Check ScheduleWaves
    #    Check Devices
    #    Check Instructors
    #    Check Students
    #    Check Tags
    #    Check Snivs
    
    def test_something(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()

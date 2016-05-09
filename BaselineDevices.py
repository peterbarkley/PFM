
import mysql.connector
import sys
from datetime import date, datetime, time, timedelta
from TrainingSquadron import TrainingSquadron
from Schedule import Schedule
from Sniv import Sniv
from Instructor import Instructor
from Odd import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Device import Device
from Wave import Wave
from Syllabus import Syllabus
from Constraint import Constraint
import vtSqlScheduler
import csv

def main():
    config = {}
    execfile(sys.argv[1], config)
    print '1'
    vt = TrainingSquadron(config)
    vtSqlScheduler.load(vt, config)
    con = mysql.connector.connect(host=config['host'],
                                  port=config['port'],
                                  user=config['user'],
                                  passwd=config['password'],
                                  db=config['database'])
    cur = con.cursor(dictionary=True)
    for i in range(3, 13):
        print i
        cur.execute("INSERT INTO resource(`created_at`, `type`, `airfield_ID`) VALUES (NOW(), 'device', 4);")
        resource_ID = cur.lastrowid
        cur.execute("""INSERT INTO `device`(`device_ID`, `device_type_ID`, `active`, `name`, `category`,
        `instructor_capacity`, `student_capacity`, `passenger_capacity`, `min_flyers`) VALUES
(%(id)s, 1, 1, %(name)s, 'aircraft', 1, 2, 0, 1);""", {'id': resource_ID, 'name': 'TC-12 ' + str(i)})

        cur.execute("""INSERT INTO `resource_tag`(`resource_ID`, `tag_ID`) VALUES (%(id)s, 1), (%(id)s, 2);""",
                    {'id': resource_ID})

        cur.execute("SELECT count(1) FROM hierarchy WHERE child = %(id)s LIMIT 1;", {'id': resource_ID})
        row = cur.fetchone()
        if row['count(1)'] == 0:
            cur.execute("INSERT INTO hierarchy(parent, child) VALUES (5, %(id)s)", {'id': resource_ID})

    con.commit()
    con.close()

if __name__ == '__main__':
    main()

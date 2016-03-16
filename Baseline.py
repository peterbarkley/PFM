
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
    vt = TrainingSquadron(config)
    vtSqlScheduler.load(vt, config)

    #  Load csv
    with open(sys.argv[2]) as csvfile:
        reader = csv.DictReader(csvfile)
        con = mysql.connector.connect(host=config['host'],
                                      port=config['port'],
                                      user=config['user'],
                                      passwd=config['password'],
                                      db=config['database'])
        cur = con.cursor(dictionary=True)
        #  Create validation sortie
        s = Sortie(instructor=Instructor(instructor_ID=11))
        s.schedule_ID = 109
        s.takeoff = datetime.now()
        s.land = datetime.now()
        s.brief = datetime.now()
        s.wave = Wave(1)

        for crow in reader:
            print(crow['first_name'], crow['last_name'])
            #  Look for student in user db, return student_ID
            cur.execute("SELECT user_ID FROM user WHERE last_name = %(last_name)s "
                        "AND (middle_name = %(middle_name)s OR middle_name IS NULL) "
                        "AND first_name = %(first_name)s "
                        "AND title = %(title)s "
                        "LIMIT 1", crow)
            row = cur.fetchone()
            if row is None:
                #  Create user and student entries
                cur.execute("INSERT INTO resource(`created_at`, `type`, `airfield_ID`) VALUES "
                            "(NOW(),'user',4)")
                student_ID = cur.lastrowid
            else:
                student_ID = row['user_ID']
            cur.execute("SELECT count(1) FROM student WHERE student_ID = %(id)s;", {'id': student_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("INSERT INTO student(student_ID, status) VALUES ("
                            "%(id)s, 'active')", {'id': student_ID})
                cur.execute("INSERT INTO student_syllabus(student_ID, syllabus_ID) "
                            "VALUES (%(id)s, %(syll)s)", {'id': student_ID, 'syll':int(crow['syllabus_ID'])})

            #  Create student sorties for each ancestor event
            event = vt.events[int(crow['next_event_ID'])]
            for a, syllabus in vt.syllabus[int(crow['syllabus_ID'])].ancestors(event):
                ss = StudentSortie()
                ss.student = Student(student_ID=student_ID)
                ss.event = a
                s.studentSorties.append(ss)
                print ss

            for i in range(1, 4):
                ss = StudentSortie()
                ss.student = Student(student_ID=student_ID)
                ss.event = vt.events[i]
                s.studentSorties.append(ss)
                print ss

        write(s, cur)
        con.commit()
        con.close()


def write(sortie, cur):

    cur.execute("INSERT INTO sortie(brief, scheduled_takeoff, scheduled_land, instructor_ID, schedule_ID, wave_ID) "
                "VALUES(%(brief)s, "
                "%(scheduled_takeoff)s, "
                "%(scheduled_land)s, "
                "%(instructor_ID)s, "
                "%(schedule_ID)s,"
                "%(wave_ID)s)",
                sortie.export())
    # Write student sorties
    sortie_ID = cur.lastrowid
    for ss in sortie.studentSorties:
        """if verbose:
            print ss.student.id, ss.event.id"""
        # Add other types of hours as well ...
        cur.execute("INSERT INTO student_sortie "
                    "(schedule_ID, sortie_ID, student_ID, event_ID, sked_flight_hours, sked_inst_hours, status) "
                    "VALUES(%(schedule_ID)s, "
                    "%(sortie_ID)s, "
                    "%(student_ID)s,%(event_ID)s,%(sked_flight_hours)s,%(sked_inst_hours)s, 'validated')",
                    {'schedule_ID': 109,
                    'sortie_ID': sortie_ID,
                    'student_ID': ss.student.student_ID,
                    'event_ID': ss.event.event_ID,
                    'sked_flight_hours': ss.event.flightHours,
                    'sked_inst_hours': ss.event.instructionalHours})




if __name__ == '__main__':
    main()

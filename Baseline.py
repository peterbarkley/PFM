
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
        s.schedule_ID = 113
        s.takeoff = datetime.now()
        s.land = datetime.now()
        s.brief = datetime.now()
        s.wave = Wave(1)

        for crow in reader:
            progressing = set()
            print(crow['first_name'], crow['last_name'])
            #  Look for student in user db, return student_ID
            cur.execute("SELECT user_ID FROM user WHERE last_name = %(last_name)s "
                        "AND (middle_name = %(middle_name)s OR middle_name IS NULL) "
                        "AND first_name = %(first_name)s "
                        "AND title = %(title)s "
                        "LIMIT 1", crow)
            row = cur.fetchone()
            if row is None:
                #  Create resource entries
                cur.execute("INSERT INTO resource(`created_at`, `type`, `airfield_ID`) VALUES "
                            "(NOW(),'user',4)")
                student_ID = cur.lastrowid
            else:
                student_ID = row['user_ID']

            student = Student(student_ID=student_ID)
            # Enter user information
            cur.execute("SELECT count(1) FROM user WHERE user_ID = %(id)s;", {'id': student_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                crow['id'] = student_ID
                cur.execute("INSERT INTO user(user_ID, last_name, first_name, middle_name, title) VALUES ("
                            "%(id)s, %(last_name)s, %(first_name)s, %(middle_name)s, %(title)s)", crow)

            # Enter student information
            cur.execute("SELECT count(1) FROM student WHERE student_ID = %(id)s;", {'id': student_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("INSERT INTO student(student_ID, status, training_end_date) VALUES ("
                            "%(id)s, 'active', %(end)s)", {'id': student_ID, 'end': crow['training_end_date']})
                cur.execute("INSERT INTO student_syllabus(student_ID, syllabus_ID) "
                            "VALUES (%(id)s, %(syll)s)", {'id': student_ID, 'syll': int(crow['syllabus_ID'])})
                student_syllabus_ID = cur.lastrowid
            else:
                cur.execute("SELECT student_syllabus_ID FROM student_syllabus WHERE student_ID = %(id)s LIMIT 1;",
                            {'id': student_ID})
                row = cur.fetchone()
                student_syllabus_ID = row['student_syllabus_ID']
            student.student_syllabus_ID = student_syllabus_ID

            # Create class if not there
            cur.execute("SELECT count(1), organization_ID FROM organization WHERE name = %(class_name)s LIMIT 1;",
                        {'class_name': "Class " + crow['class']})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("INSERT INTO resource(`created_at`, `type`, `airfield_ID`) VALUES "
                            "(NOW(),'organization',4)")
                class_ID = cur.lastrowid
                cur.execute("""INSERT INTO organization(organization_ID, name, scheduling) VALUES
                (%(id)s, %(class_name)s, 0)""", {'id': class_ID, 'class_name': "Class " + crow['class']})
                cur.execute("INSERT INTO hierarchy(parent, child) VALUES (5, %(id)s)", {'id': class_ID})
            else:
                class_ID = row['organization_ID']

            # Associate student with VT-35
            cur.execute("SELECT count(1) FROM hierarchy WHERE child = %(id)s LIMIT 1;", {'id': student_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("INSERT INTO hierarchy(parent, child) VALUES (5, %(id)s)", {'id': student_ID})

            # Insert resource_tags

            cur.execute("SELECT count(1) FROM resource_tag WHERE resource_ID = %(id)s LIMIT 1;", {'id': student_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("""INSERT INTO resource_tag(resource_ID, tag_ID) VALUES (%(id)s, 1),
                    (%(id)s, 2),
                    (%(id)s, 3),
                    (%(id)s, 4),
                    (%(id)s, 5),
                    (%(id)s, 7),
                    (%(id)s, 8),
                    (%(id)s, 9),
                    (%(id)s, 10)""", {'id': student_ID})
            """# Pull progressing events
            cur.execute("SELECT * FROM student_sortie "
                "LEFT JOIN student ON student.student_ID = student_sortie.student_ID "
                "LEFT JOIN hierarchy ON student.student_ID = child "
                "LEFT JOIN student_syllabus "
                "ON student_sortie.student_syllabus_ID = student_syllabus.student_syllabus_ID "
                "LEFT JOIN sortie ON sortie.sortie_ID = student_sortie.sortie_ID "
                "LEFT JOIN schedule ON schedule.schedule_ID = student_sortie.schedule_ID "
                "WHERE student.student_ID = %(id)s "
                "AND (hierarchy.stop > NOW() OR hierarchy.stop IS NULL) "
                "AND student_syllabus.outcome IS NULL AND student_sortie.progressing_event = 1 "
                "AND schedule.published = TRUE",
                {'id': student_ID})"""

            # Create student sorties for each ancestor event
            event = vt.events[int(crow['latest_event_ID'])]
            ss = StudentSortie()
            ss.student = student
            ss.event = event
            s.studentSorties.append(ss)
            for a, syllabus in vt.syllabus[int(crow['syllabus_ID'])].ancestors(event):
                ss = StudentSortie()
                ss.student = student
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
        cur.execute("""INSERT INTO student_sortie (schedule_ID, sortie_ID, student_ID, event_ID, sked_flight_hours,
        sked_inst_hours, status, student_syllabus_ID, computer_generated)
        VALUES(%(schedule_ID)s, %(sortie_ID)s, %(student_ID)s, %(event_ID)s, %(sked_flight_hours)s, %(sked_inst_hours)s,
        'validated', %(ss_ID)s, 1)""",
                    {'schedule_ID': 109,
                    'sortie_ID': sortie_ID,
                    'student_ID': ss.student.student_ID,
                    'event_ID': ss.event.event_ID,
                    'sked_flight_hours': ss.event.flightHours,
                    'sked_inst_hours': ss.event.instructionalHours,
                     'ss_ID': ss.student.student_syllabus_ID})




if __name__ == '__main__':
    main()

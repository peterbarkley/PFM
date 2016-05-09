
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
    with open(sys.argv[2]) as csvfile:
        reader = csv.DictReader(csvfile)
        con = mysql.connector.connect(host=config['host'],
                                      port=config['port'],
                                      user=config['user'],
                                      passwd=config['password'],
                                      db=config['database'])
        cur = con.cursor(dictionary=True)
        print '4'
        for crow in reader:
            print(crow['first_name'], crow['last_name'])
            #  Look for instructor in user db, return instructor_ID
            cur.execute("SELECT user_ID FROM user WHERE last_name = %(last_name)s "
                        "AND (middle_name = %(middle_name)s OR middle_name IS NULL) "
                        "AND first_name = %(first_name)s "
                        "AND title = %(title)s "
                        "LIMIT 1", crow)
            row = cur.fetchone()
            print row
            if row is None:
                #  Create resource entries
                cur.execute("INSERT INTO resource(`created_at`, `type`, `airfield_ID`) VALUES "
                            "(NOW(),'user',4)")
                instructor_ID = cur.lastrowid
            else:
                instructor_ID = row['user_ID']

            print instructor_ID
            instructor = Instructor(instructor_ID=instructor_ID)
            # Enter user information
            cur.execute("SELECT count(1) FROM user WHERE user_ID = %(id)s;", {'id': instructor_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                crow['id'] = instructor_ID
                cur.execute("INSERT INTO user(user_ID, last_name, first_name, middle_name, title, role) VALUES ("
                            "%(id)s, %(last_name)s, %(first_name)s, %(middle_name)s, %(title)s, 'instructor')", crow)

            # Enter instructor information
            cur.execute("SELECT count(1) FROM instructor WHERE instructor_ID = %(id)s;", {'id': instructor_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("INSERT INTO instructor(instructor_ID, active) VALUES (%(id)s, 1)", {'id': instructor_ID})

            # Associate instructor with VT-35
            cur.execute("SELECT count(1) FROM hierarchy WHERE child = %(id)s LIMIT 1;", {'id': instructor_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("INSERT INTO hierarchy(parent, child) VALUES (5, %(id)s)", {'id': instructor_ID})

            # Insert resource_tags

            cur.execute("SELECT count(1) FROM resource_tag WHERE resource_ID = %(id)s LIMIT 1;", {'id': instructor_ID})
            row = cur.fetchone()
            if row['count(1)'] == 0:
                cur.execute("""INSERT INTO resource_tag(resource_ID, tag_ID) VALUES (%(id)s, 1), (%(id)s, 3),
(%(id)s, 4), (%(id)s, 5), (%(id)s, 7),  (%(id)s, 8), (%(id)s, 10)""", {'id': instructor_ID})

        con.commit()
        con.close()

if __name__ == '__main__':
    main()


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
from Plane import Plane
from Wave import Wave


verbose = True


def main():
    config = {}
    execfile(sys.argv[1], config)
    vt = TrainingSquadron(config)
    global verbose
    verbose = config['verbose']
    load(vt, config)
    if verbose:
        print vt.__dict__
    solved = vt.writeSchedules()
    if vt.hardschedule and not solved:
        vt.hardschedule = 0
        solved = vt.writeSchedules()

    if solved:
        if verbose:
            print "Writing solved model to database"
        write(vt, config)

    return 0


def load(vt, config):
    if verbose:
        print "Loading model from database"

    try:
        con = mysql.connector.connect(host=config['host'],
                                      port=config['port'],
                                      user=config['user'],
                                      passwd=config['password'],
                                      db=config['database'])
        cur = con.cursor(dictionary=True)
        days = config['days']

        loadSchedules(vt, cur)
        loadWaves(vt, cur)
        loadScheduleWaves(vt, cur)
        loadEvents(vt, cur)
        loadDevices(vt, cur)
        loadInstructors(vt, cur)
        loadStudents(vt, cur)
        loadSnivs(vt, cur)

    finally:
        con.commit()
        con.close()


# Loads all of the required schedules or creates them if they don't exist.
def loadSchedules(vt, cur):
    if verbose:
        print "Loading schedules from database"

    d = date.today() + timedelta(days=1)
    cur.execute("SELECT *, MIN(day) minday FROM schedule "
                "WHERE published = 0 "
                "AND day >= %(day)s "
                "AND organization_ID = %(organization_ID)s LIMIT 1",
                {'day': d, 'organization_ID': vt.organization_ID})
    i = 1
    row = cur.fetchone()
    while i <= vt.days:
        if not row or not row['schedule_ID']:
            row = insertSchedule(vt, d, cur)
        s = Schedule(row)
        s.flyDay = i
        s.priority = i ** (-0.5)
        if verbose:
            print 'Computing schedule for schedule ID %d, flight day %d, day %s, with priority %s' % \
                  (s.schedule_ID, s.flyDay, s.day, s.priority)
        vt.schedules[i] = s
        d = row['day'] + timedelta(days=1)
        cur.execute("SELECT * FROM schedule "
                    "WHERE published = False "
                    "AND day = %(day)s "
                    "AND organization_ID = %(organization_ID)s "
                    "LIMIT 1", {'day': d, 'organization_ID': vt.organization_ID})
        row = cur.fetchone()
        i += 1
    pass


def insertSchedule(vt, d, cur):
    if verbose:
        print 'Inserting schedule for day %s' % str(d)
    # Future work: add sunrise and sunset from sun = vt.airfield.getSun(d, True); sun['sunrise'], sun['sunset']
    row = {'day': d, 'organization_ID': vt.organization_ID, 'blank': 0}
    cur.execute('INSERT INTO schedule (day, organization_ID, blank) '
                'VALUES (%(day)s, %(organization_ID)s, %(blank)s)', row)

    row['schedule_ID'] = cur.lastrowid
    return row


def loadWaves(vt, cur):
    pass


def loadScheduleWaves(vt, cur):
    pass


def loadEvents(vt, cur):
    pass


def loadDevices(vt, cur):
    pass


def loadInstructors(vt, cur):
    pass


def loadStudents(vt, cur):
    pass


def loadSnivs(vt, cur):
    pass


def write(vt, config):

    try:
        con = mysql.connector.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['database'])
        cur = con.cursor(dictionary=True)
        days = config['days']

    finally:
        con.close()


if __name__ == '__main__':
    main()

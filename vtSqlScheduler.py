
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
        for d in vt.devices.values():
            print d.__dict__
        for i in vt.instructors.values():
            print i.__dict__
        for s in vt.students.values():
            print s.__dict__
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

        loadSyllabi(vt, cur)
        loadSchedules(vt, cur)
        loadForecast(vt, cur)
        loadScheduleWaves(vt, cur)
        loadDevices(vt, cur)
        loadInstructors(vt, cur)
        loadStudents(vt, cur)
        loadTags(vt,cur)
        loadSnivs(vt, cur)

    finally:
        con.commit()
        con.close()


def loadSyllabi(vt, cur):
    if verbose:
        print "Loading syllabi"
    cur.execute("SELECT syllabus.syllabus_ID, `name`, syllabus.organization_ID, syllabus.device_type_ID, `precedence` "
                "FROM `syllabus` LEFT JOIN student_syllabus ON syllabus.syllabus_ID = student_syllabus.syllabus_ID "
                "LEFT JOIN student ON student.student_ID = student_syllabus.student_ID "
                "LEFT JOIN hierarchy ON child = student.student_ID "
                "WHERE student.status = 'active' AND parent = %(parent)s "
                "AND (student_syllabus.stop > NOW() OR student_syllabus.stop IS NULL) "
                "AND (hierarchy.stop > NOW() OR hierarchy.stop IS NULL) "
                "GROUP BY syllabus.syllabus_ID",
                {'parent': vt.organization_ID})
    for row in cur:
        vt.syllabus[row['syllabus_ID']] = Syllabus(row)

    loadEvents(vt, cur)


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
    print vt.days
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


def loadForecast(vt, cur):
    pass


def loadWaves(vt, cur):
    if verbose:
        print "Loading waves"
    cur.execute('SELECT * FROM wave '
                'LEFT JOIN wave_tag on wave.wave_ID = wave_tag.wave_ID '
                'LEFT JOIN tag ON wave_tag.tag_ID = tag.tag_ID '
                'WHERE tag.name = "default" AND organization_ID = %(organization_ID)s',
                {'organization_ID': vt.organization_ID})

    return cur.fetchall()


# Create waves for each schedule
def loadScheduleWaves(vt, cur):
    default_waves = None

    # Get wave tags
    cur.execute("SELECT * FROM wave_tag LEFT JOIN tag ON wave_tag.tag_ID = tag.tag_ID "
                "WHERE organization_ID = %(organization_ID)s "
                "AND tag.name != 'default'",
                {'organization_ID': vt.organization_ID})
    wave_tags = {}
    for w in cur:
        if not w['wave_ID'] in wave_tags:
            wave_tags[w['wave_ID']] = []
        wave_tags[w['wave_ID']].append(w['name'])
    for s in vt.schedules.values():
        if not s.blank:
            if s.use_default_waves:
                if not default_waves:
                    default_waves = loadWaves(vt, cur)
                waves = default_waves
            else:
                cur.execute("SELECT * FROM schedule_wave LEFT JOIN wave WHERE schedule_ID = %(schedule_ID)s", {'schedule_ID': s.id})
                waves = cur.fetchall()
        createWaves(vt, s, waves, wave_tags)
    if verbose:
        print "Waves loaded"


def createWaves(vt, s, waves, wave_tags):
    for wave_entry in waves:
        # if verbose: print row["schedule_ID"],row["wave_ID"],row["priority"]
        i = wave_entry['wave_ID']
        w = Wave(i)
        # Plane times
        midnight = datetime.combine(s.day, time(0))
        start_time = midnight + wave_entry["device_start"]
        end_time = midnight + wave_entry["device_end"]
        w.begin = start_time
        w.end = end_time
        w.times["Plane"].begin = start_time
        w.times["Plane"].end = end_time
        #Flyer times
        start_time = midnight + wave_entry["flyer_start"]
        end_time = midnight + wave_entry["flyer_end"]
        w.times["Flyer"].begin = start_time
        w.times["Flyer"].end = end_time
        w.schedule = s
        w.priority = vt.wavePriority(w)
        if wave_entry["student_multiple"] is not None:
            w.studentMultiple = float(wave_entry["student_multiple"])
        w.tags = wave_tags.get(i)
        s.waves[i] = w
    s.findExclusiveWaves()


def loadEvents(vt, cur):
    if verbose:
        print "Loading events"
    query = "SELECT * FROM event LEFT JOIN event_hierarchy ON event.event_ID = event_hierarchy.parent_event "\
            "WHERE event_hierarchy.syllabus_ID IS NULL "
    for s in vt.syllabus:
        query += "OR event_hierarchy.syllabus_ID = %s " % s

    cur.execute(query)
    for row in cur:
        if not row['event_ID'] in vt.events:
            vt.events[row['event_ID']] = Event(row)
        s = row['syllabus_ID']
        if s in vt.syllabus:
            vt.syllabus[s].event_arcs += (row['parent_event'], row['child_event'])
            vt.syllabus[s].events.add(vt.events[row['event_ID']])


# Load all active devices for the squadron
def loadDevices(vt, cur):
    if verbose:
        print "Loading devices"
    cur.execute("SELECT * FROM device LEFT JOIN hierarchy ON device_ID = child "
                "WHERE active = TRUE AND parent = %(parent)s "
                "AND (stop > NOW() OR stop IS NULL)",
                {'parent': vt.organization_ID})
    for row in cur:
        d = Device(row)
        vt.devices[d.device_ID] = d
        print d.name, d.category

    pass


def loadInstructors(vt, cur):
    if verbose:
        print "Loading Instructors"
    cur.execute("SELECT instructor_ID, paid, max_events FROM instructor LEFT JOIN hierarchy ON instructor_ID = child "
                "WHERE active = TRUE AND parent = %(parent)s "
                "AND (stop > NOW() OR stop IS NULL)",
                {'parent': vt.organization_ID})
    for row in cur:
        inst = Instructor(row)
        vt.instructors[inst.instructor_ID] = inst


def loadStudentSyllabi(vt, cur):
    cur.execute("SELECT student.student_ID, student_syllabus.syllabus_ID "
                "FROM student_syllabus "
                "LEFT JOIN student ON student.student_ID = student_syllabus.student_ID "
                "LEFT JOIN hierarchy ON child = student.student_ID "
                "WHERE student.status = 'active' AND parent = %(parent)s "
                "AND (student_syllabus.stop > NOW() OR student_syllabus.stop IS NULL) "
                "AND (hierarchy.stop > NOW() OR hierarchy.stop IS NULL)",
                {'parent': vt.organization_ID})

    for s in cur:
        syll = vt.syllabus[s['syllabus_ID']]
        vt.students[s['student_ID']].syllabus[syll.precedence] = syll


def loadStudents(vt, cur):
    if verbose:
        print "Loading Students"

    cur.execute("SELECT student_ID, onwing_instructor_ID, partner_student_ID, last_flight, priority "
                "FROM student LEFT JOIN hierarchy ON student_ID = child "
                "WHERE student.status = 'active' AND parent = %(parent)s "
                "AND (stop > NOW() OR stop IS NULL)",
                {'parent': vt.organization_ID})
    for row in cur:
        s = int(row["student_ID"])
        if verbose:
            print 'Student id ', s
        stud = Student(row, squadron=vt)
        vt.students[s] = stud


    loadStudentSyllabi(vt, cur)
    loadStudentEvents(vt, cur)


def loadStudentEvents(vt, cur):
    cur.execute("SELECT * FROM student_sortie "
                "LEFT JOIN student ON student.student_ID = student_sortie.student_ID "
                "LEFT JOIN hierarchy ON student.student_ID = child "
                "LEFT JOIN student_syllabus ON student_sortie.student_syllabus_ID = student_syllabus.student_syllabus_ID "
                "LEFT JOIN sortie ON sortie.sortie_ID = student_sortie.sortie_ID "
                "WHERE student.status = 'active' AND parent = %(parent)s "
                "AND (hierarchy.stop > NOW() OR hierarchy.stop IS NULL) "
                "AND sortie.scheduled_land >= hierarchy.start",
                {'parent': vt.organization_ID})
    for row in cur:
        # Add progressing events to set for student
        if row['progessing_event'] == 1:
            stud = vt.students[row['student_ID']]
            stud.progressing += (row['event_ID'], vt.syllabus[row['syllabus_ID']])

        # Future work: reduce available plane hours based on scheduled events

        # Prepare to add crew rest snivs
        end = row['scheduled_land']
        if row['event_ID'] in vt.events:
            e = vt.events[row['event_ID']]
            end += e.getDebriefHours()
        first_start = datetime.combine(vt.schedules[1].day, time())
        i = -1 * row['student_sortie_ID']

        # Create crew rest sniv for student
        if row['student_ID'] in vt.students:
            stud = vt.students[row['student_ID']]
            if end + stud.crewRest >= first_start:
                s = Sniv()
                s.begin = end
                s.end = end + stud.crewRest
                stud.snivs[i] = s

        # Create crew rest sniv for instructor
        if row['instructor_ID'] in vt.instructors:
            inst = vt.instructors[row['instructor_ID']]
            if end + inst.crewRest >= first_start:
                s = Sniv()
                s.begin = end
                s.end = end + inst.crewRest
                inst.snivs[i] = s


# Loads tags for devices, students and instructors
def loadTags(vt, cur):
    cur.execute("SELECT resource_ID, tag.tag_ID, expiration, object_resource_ID, object_tag_ID, name, length FROM resource_tag "
                "LEFT JOIN tag ON resource_tag.tag_ID = tag.tag_ID "
                "LEFT JOIN hierarchy ON resource_tag.resource_ID = child "
                "WHERE parent = %(parent)s "
                "AND (stop > NOW() OR stop IS NULL) "
                "AND (expiration > NOW() OR expiration IS NULL)",
                {'parent': vt.organization_ID})
    tags = {}
    for tag in cur:
        if not tag['resource_ID'] in tags:
            tags[tag['resource_ID']] = {}
        tags[tag['resource_ID']][tag['tag_ID']] = tag
    for d in vt.devices.values():
        if d.device_ID in tags:
            d.tags.update(tags[d.device_ID])
    for i in vt.instructors.values():
        if i.instructor_ID in tags:
            i.tags.update(tags[i.instructor_ID])
    for s in vt.students.values():
        if s.student_ID in tags:
            s.tags.udpate(tags[s.student_ID])


def loadSnivs(vt, cur):
    if verbose:
        print "Loading snivs"
    end = vt.schedules[vt.days].day + timedelta(days=1)
    cur.execute("SELECT `sniv_ID`, sniv.resource_ID, `begin`, `end`, `reason`, `approval`, `repeated` FROM sniv "
                "LEFT JOIN hierarchy ON child = sniv.resource_ID "
                "WHERE sniv.approval = 1 AND (parent = %(parent)s OR sniv.resource_ID = %(parent)s)"
                "AND (hierarchy.stop > NOW() OR hierarchy.stop IS NULL) "
                "AND end > NOW() AND begin < %(end_date)s",
                {'parent': vt.organization_ID, 'end_date': end})
    for row in cur:
        s = Sniv(row)
        r = row['resource_ID']
        if r in vt.devices:
            vt.devices[r].snivs[row['sniv_ID']] = s
        else:
            if r in vt.students:
                vt.students[r].snivs[row['sniv_ID']] = s
            if r in vt.instructors:
                vt.instructors[r].snivs[row['sniv_ID']] = s


def write(vt, config):

    try:
        con = mysql.connector.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['database'])
        cur = con.cursor(dictionary=True)
        days = config['days']

    finally:
        con.close()


if __name__ == '__main__':
    main()

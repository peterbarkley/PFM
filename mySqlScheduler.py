#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      pbarkley
#
# Created:     01/04/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import MySQLdb as mdb
import sys
import decimal
from datetime import date, datetime, time, timedelta
from Squadron import Squadron
from Schedule import Schedule
from Sniv import Sniv
from Flyer import Flyer
from Instructor import Instructor
from Student import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Plane import Plane
from Wave import Wave

verbose = True;

def main():
    config = {}
    execfile(sys.argv[1], config)
    vtna = Squadron()
    vtna.verbose = verbose
    if verbose:
        print "Loading model from database"
    load(vtna,config)
    if verbose:
        print "Solving model"
    vtna.writeSchedules()
    if verbose:
        print "Writing model to database"
    writeToDatabase(vtna,config)
    #if verbose: print "Date loaded"


def load(vtna,config):

    con = mdb.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['db'])
    with con:
        cur = con.cursor()
        cur.execute("SELECT VERSION()")

        ver = cur.fetchone()

        if verbose:
            print "Database version : %s " % ver

        cur = con.cursor(mdb.cursors.DictCursor)

        #Loop over schedule table where not published and flight_day != NULL and add schedules for each flight_day
        cur.execute("SELECT * FROM schedule WHERE (published = FALSE AND flight_day IS NOT NULL)") # AND NOT flight_day = NULL
        rows = cur.fetchall()

        for row in rows:
            i = int(row["flight_day"])
            day = row["day"]
            sked=Schedule(day)
            sked.flyDay = i
            sked.id = int(row["schedule_ID"])

            #Set priority
            if row["priority"]!=None:
                sked.priority = float(row["priority"])
            if verbose:
                print 'Computing schedule for schedule ID %d, flight day %d, day %s, with priority %d '% (sked.id, sked.flyDay, day,sked.priority)
            vtna.schedules[i]=sked
        vtna.totalFlightDays = len(rows)

        #Find waves
        cur.execute("SELECT * FROM wave")
        rows = cur.fetchall()
        waves = {}
        for row in rows:
            waves[int(row["wave_ID"])]=row

        #Create waves for each schedule
        for d in vtna.schedules:
            sked = vtna.schedules[d]
            sked.waves = {}
            cur.execute("SELECT * FROM schedule_wave WHERE schedule_ID = %s",(sked.id))
            rows = cur.fetchall()
            createWaves(sked,rows,waves)
        if verbose:
            print "Waves loaded"

        #Create events for squadron
        cur.execute("SELECT * FROM event")
        rows = cur.fetchall()
        for row in rows:
            i = int(row["event_ID"])
            e = Event(i)
            if row["check_instructor_req"]:
                e.check = True
            if row["onwing_req"]:
                e.onwing = True
            elif row["not_onwing_req"]:
                e.offwing = True
            e.flightHours = float(row["dual_flight_hours"])+float(row["solo_flight_hours"])
            e.planeHours = float(row["ground_plane_hours"])
            total_inst = float(row["ground_nonplane_hours"])+e.planeHours + e.flightHours
            e.instructionalHours = total_inst
            e.syllabus = int(row["syllabus_ID"])
            if row["follows_immediately"]:
                e.followsImmediately = True
            vtna.syllabus[i]=e

            #Set event precedence and following
        cur.execute("SELECT * FROM event_precedence")
        rows = cur.fetchall()
        for row in rows:
            i = int(row["following_event_ID"])
            j = int(row["preceding_event_ID"])
            print i,' follows ', j
            vtna.syllabus[i].precedingEvents.add(vtna.syllabus[j])
            vtna.syllabus[j].followingEvents.add(vtna.syllabus[i])
        if verbose:
            print "Events loaded"

        #Loop over planes
        cur.execute("SELECT * FROM plane WHERE active=TRUE")
        rows = cur.fetchall()
        for row in rows:
            #if verbose: print row["tail_number"],row["plane_type_ID"],row["max_cargo"]
            p =row["tail_number"]
            plane = Plane(p)
            plane.planetype = row["plane_type_ID"]
            plane.hours = float(row["hours"])
            if (row["max_cargo"]!= 0 and row["max_cargo"]!= None):
                plane.maxWeight = row["max_cargo"]
            vtna.planes[p]=plane

            #Add plane types

        #Add plane availability
        cur.execute("SELECT * FROM plane_unavail WHERE (end >= %s and start <= %s)",(vtna.schedules[1].date.strftime('%Y-%m-%d'),vtna.schedules[vtna.totalFlightDays].date.strftime('%Y-%m-%d')))
        rows = cur.fetchall()
        i=1
        for row in rows:
            p=row["plane_tail_number"]
            #if verbose: print p,row["start"],row["end"]
            if p in vtna.planes:
                plane = vtna.planes[p]
                s = Sniv()
                s.begin = row["start"]
                s.end = row["end"]
                plane.snivs[i]=s
                i=i+1
        if verbose:
            print "Planes loaded"

        #Loop over instructors, adding them
        cur.execute("SELECT * FROM cfi WHERE active = TRUE")
        rows = cur.fetchall()
        for row in rows:
            c = int(row["CFI_ID"])
            #if verbose: print c
            inst = Instructor(c)
            inst.maxEvents = row["max_events"]
            if row["C990"]:
                inst.check = True
            vtna.instructors[c]=inst
        if verbose:
            print "Instructors loaded"

        #Loop over students, adding them
        cur.execute("SELECT * FROM student WHERE status = 'active'")
        rows = cur.fetchall()
        for row in rows:
            s = int(row["student_ID"])
            if verbose:
                print 'Student id ',s
            stud = Student(s,vtna)
            stud.syllabus = int(row["syllabus_ID"])
            if row["priority"] != None:
                stud.priority = float(row["priority"])
            cfi = row["onwing_CFI_ID"]
            if cfi in vtna.instructors:
                #if verbose: print "Add instructor",cfi
                stud.onwing = vtna.instructors[cfi]
            vtna.students[s]= stud
            partner_ID = row["partner_student_ID"]
            if partner_ID in vtna.students:
                #if verbose: print "Add partners",s,partner_ID
                stud.partner=vtna.students[partner_ID]
                vtna.students[partner_ID].partner = stud
        if verbose:
            print "Students loaded"

        #Add weight for students & CFIs
        cur.execute("SELECT * FROM user")
        rows = cur.fetchall()
        for row in rows:
            id = row["user_ID"]
            if row["weight"] != None:
                if id in vtna.students:
                    vtna.students[id].weight = int(row["weight"])
                elif id in vtna.instructors:
                    vtna.instructors[id].weight = int(row["weight"])
        if verbose:
            print "Weights loaded"

        #Add plane quals for students & CFIs
        cur.execute("SELECT * FROM plane_quals")
        rows = cur.fetchall()
        for row in rows:
            id = row["user_ID"]
            if id in vtna.students:
                vtna.students[id].quals.append(row["plane_type_ID"])
            elif id in vtna.instructors:
                vtna.instructors[id].quals.append(row["plane_type_ID"])
        if verbose:
            print "Quals loaded"

        #Add snivs for students & CFIs
        cur.execute("SELECT * FROM sniv WHERE (end >= %s and start <= %s and approval=TRUE)",(vtna.schedules[1].date.strftime('%Y-%m-%d'),vtna.schedules[vtna.totalFlightDays].date.strftime('%Y-%m-%d')))
        rows = cur.fetchall()
        i=1
        for row in rows:
            id = row["user_ID"]
            if verbose:
                print id,row["start"],row["end"]
            if id in vtna.students:
                s = Sniv()
                s.begin = row["start"]
                s.end = row["end"]
                vtna.students[id].snivs[i]=s
                i=i+1
            elif id in vtna.instructors:
                s = Sniv()
                s.begin = row["start"]
                s.end = row["end"]
                vtna.instructors[id].snivs[i]=s
                i=i+1

        if verbose:
            print "Snivs loaded"

        #Load most recent published schedule as schedule.today()
        cur.execute("SELECT * FROM schedule WHERE published=TRUE ORDER BY day DESC")
        row = cur.fetchone()
        vtna.today.id = int(row["schedule_ID"])
        vtna.today.date = row["day"]
        cur.execute("SELECT * FROM schedule_wave WHERE schedule_ID = %s",(vtna.today.id))
        rows = cur.fetchall()
        createWaves(vtna.today,rows,waves)

        cur.execute("SELECT * FROM sortie WHERE schedule_ID = %s",(vtna.today.id))
        rows = cur.fetchall()
        for row in rows:
            s = Sortie()
            id = int(row["sortie_ID"])
            if verbose:
                print id,row["CFI_ID"]
            s.brief = row["brief"]
            cfi_id = int(row["CFI_ID"])
            if cfi_id in vtna.instructors:
                s.instructor = vtna.instructors[cfi_id] #Instructor
                s.studentSorties = []
                s.takeoff = row["scheduled_takeoff"]
                s.land = row["scheduled_land"]
                if row["wave_ID"] != None:
                    s.wave = vtna.today.waves[int(row["wave_ID"])] #Wave ojbect
                else:
                    s.wave = vtna.today.waves[1] #This is a bad hack. Ought to use a function to determine nearest wave in today's set of waves
                vtna.today.sorties[id]=s

        #Create sorties and studentSorties from the entries in those table corresponding to the most recent published sked
        cur.execute("SELECT * FROM student_sortie WHERE (status = 'pass' OR status = 'marginal' OR status = 'scheduled')")
        rows = cur.fetchall()
        for row in rows:
            s = int(row["student_ID"])
            if s in vtna.students:
                stud = vtna.students[s]
                event = vtna.syllabus[int(row["event_ID"])]
                if row["status"]=="scheduled":
                    stud.scheduledEvents.add(event)
                else:
                    stud.completedEvents.add(event)
                if row["sortie_ID"] in vtna.today.sorties:
                    sortie = vtna.today.sorties[row["sortie_ID"]]
                    ss = StudentSortie()
                    ss.student=vtna.students[s]
                    ss.event=event
                    sortie.plane = vtna.planes[row["plane_tail_number"]]
                    sortie.studentSorties.append(ss)
                    if vtna.today.date == vtna.schedules[1].date+timedelta(days=1):
                        sniv = Sniv()
                        sniv.begin = sortie.brief
                        sniv.end = sortie.wave.times["Flyer"].end + stud.crewRest
                        stud.snivs[0]=sniv

        for s in vtna.students:
            stud = vtna.students[s]
            i=1
            for event in stud.findPossible(1,True):
                print 'student ', s, 'possible event ', event.id
                if i==1:
                    stud.nextEvent = event
                i=i+1



def createWaves(sked,rows,waves):
    for row in rows:
        i = int(row["wave_ID"])
        wave_entry = waves[i]
        #if verbose: print row["schedule_ID"],row["wave_ID"],row["priority"]
        w = Wave(i)
        #Plane times
        midnight = datetime.combine(sked.date,time(0))
        start_time =midnight+wave_entry["plane_start"]
        end_time = midnight+wave_entry["plane_end"]
        w.begin = start_time
        w.end = end_time
        w.times["Plane"].begin = start_time
        w.times["Plane"].end = end_time
        #Flyer times
        start_time = midnight+wave_entry["flyer_start"]
        end_time = midnight+wave_entry["flyer_end"]
        w.times["Flyer"].begin = start_time
        w.times["Flyer"].end = end_time
        w.schedule = sked
        w.priority = float(row["priority"])
        sked.waves[i]=w
    sked.findExclusiveWaves()

def writeToDatabase(vtna,config):

    con = mdb.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['db'])

    with con:
        cur = con.cursor(mdb.cursors.DictCursor)

        for d in vtna.schedules:

            sked = vtna.schedules[d]
            day = sked.date

            cur.execute("SELECT * FROM schedule WHERE day=%s AND published=0",(day.strftime('%Y-%m-%d %H-%M-%S'))) # AND NOT flight_day = NULL
            row = cur.fetchone()
            """if rows == ():
                cur.execute("INSERT INTO schedule(day) VALUES(%s)",(day.strftime('%Y-%m-%d %H-%M-%S')))
                cur.execute("SELECT * FROM schedule WHERE day=%s",(day.strftime('%Y-%m-%d %H-%M-%S')))
                row = cur.fetchone()
                sked.id = row["schedule_ID"]
            else:"""
                #for row in rows:
            if row != None:
                sked.id = row["schedule_ID"]
                if verbose:
                    print sked.id
                cur.execute("DELETE FROM student_sortie WHERE schedule_ID=%s",(sked.id))
                cur.execute("DELETE FROM sortie WHERE schedule_ID=%s",(sked.id))
                #Delete student sorties?

                for s in sked.sorties:
                    sortie = sked.sorties[s]
                    statement = "INSERT INTO sortie(brief,scheduled_takeoff,scheduleD_land,CFI_ID,schedule_ID,wave_ID) VALUES(%s,%s,%s,%d,%s,%d)",(sortie.brief.strftime('%H:%M:%S'),
                        sortie.takeoff.strftime('%H:%M:%S'),
                        sortie.land.strftime('%H:%M:%S'),
                        int(sortie.instructor.id),
                        int(sked.id),
                        int(sortie.wave.id));
                    if verbose:
                        print statement
                    cur.execute("INSERT INTO sortie(sortie_ID,brief,scheduled_takeoff,scheduleD_land,CFI_ID,schedule_ID,wave_ID) VALUES(NULL,%s,%s,%s,%s,%s,%s)",(
                        sortie.brief.strftime('%H:%M:%S'),
                        sortie.takeoff.strftime('%H:%M:%S'),
                        sortie.land.strftime('%H:%M:%S'),
                        int(sortie.instructor.id),
                        int(sked.id),
                        int(sortie.wave.id)))
                    cur.execute("SELECT sortie_ID FROM sortie ORDER BY sortie_ID DESC LIMIT 1")
                    row = cur.fetchone()
                    sortie_id=row["sortie_ID"]
                    if verbose:
                        print 'Sortie ID: ', sortie_id
                    for ss in sortie.studentSorties:
                        if verbose:
                            print ss.student.id, ss.event.id
                        cur.execute("INSERT INTO student_sortie(schedule_ID,sortie_ID,student_ID,event_ID,sked_flight_hours,sked_inst_hours,plane_tail_number) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (sked.id,
                            sortie_id,
                            ss.student.id,
                            ss.event.id,
                            ss.event.flightHours,
                            ss.event.instructionalHours,
                            sortie.plane.id))

if __name__ == '__main__':
    main()

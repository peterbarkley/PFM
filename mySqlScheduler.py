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
import mysql.connector
import sys
import decimal
from datetime import date, datetime, time, timedelta
from Squadron import Squadron
from Schedule import Schedule
from Sniv import Sniv
from Flyer import Flyer
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
    vtna = Squadron(config)
    global verbose
    verbose = config['verbose']
    """vtna.verbose = config['verbose']
    vtna.timeLimit = config['timeLimit']
    vtna.backToBack = config['backToBack']
    vtna.hardschedule = 1 #config['hardschedule']
    if 'hardschedule' in config:
        vtna.hardschedule = config['hardschedule']
    if 'sufficientTime' in config:
        vtna.sufficientTime = config['sufficientTime']
    if 'militaryPreference' in config:
        vtna.militaryPreference = config['militaryPreference']"""

    if verbose:
        print "Loading model from database"
    load(vtna, config)
    if verbose:
        print "Solving model"
    solved = vtna.writeSchedules()
    if not solved:
        vtna.hardschedule = 0
        solved = vtna.writeSchedules()

    if solved:
        if verbose:
            print "Writing model to database"
        writeToDatabase(vtna,config)
    #if verbose: print "Date loaded"
    return 0

def load(vtna, config):

    # con = mdb.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['database'])
    con = mysql.connector.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['database'])
    try: # with con:
        # cur = con.cursor()
        cur = con.cursor(dictionary=True)
        # cur = con.cursor(mdb.cursors.DictCursor)
        days = config['days']
        if days > 3:
            vtna.calculateMaintenance = True

        # Loop over schedule table where not published and flight_day != NULL and add schedules for each flight_day
        # Ought to sort by date and not pull past schedules - day >= date.today()!
        query = "SELECT * FROM schedule WHERE published = FALSE ORDER BY day ASC LIMIT %d" % days
        cur.execute(query) # AND NOT flight_day = NULL
        i=1
        rows = cur.fetchall() # .fetchmany(size=days)

        for row in rows:
            sked = Schedule(row)
            sked.flyDay = i
            # Set priority
            sked.priority = i ** (-0.5)  # priorities[i]
            if verbose:
                print 'Computing schedule for schedule ID %d, flight day %d, day %s, with priority %s'% (sked.id, sked.flyDay, sked.day, sked.priority)
            vtna.schedules[i] = sked
            i += 1

        vtna.days = len(rows)

        #Find waves
        cur.execute("SELECT * FROM wave")
        rows = cur.fetchall()
        waves = {}
        for row in rows:
            waves[int(row["wave_ID"])]=row

        #Create waves for each schedule
        for d in vtna.schedules:
            sked = vtna.schedules[d]
            if not sked.blank:
                sked.waves = {}# %(emp_no)s"
                    # cursor.execute(select_stmt, { 'emp_no': 2 })
                cur.execute("SELECT * FROM schedule_wave WHERE schedule_ID = %(schedule_ID)s", {'schedule_ID': sked.id})
                rows = cur.fetchall()
                createWaves(sked,rows,waves)
        if verbose:
            print "Waves loaded"

        #Create events for squadron
        cur.execute("SELECT * FROM event")
        rows = cur.fetchall()
        for row in rows:
            i = int(row["event_ID"])
            e = Event(event_ID = i)
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
            e.max_students = int(row["max_students"])
            if row["follows_immediately"] != None and int(row["follows_immediately"]) == 1:
                e.followsImmediately = True
            vtna.syllabus[i]=e

            #Set event precedence and following
        cur.execute("SELECT * FROM event_precedence")
        rows = cur.fetchall()
        for row in rows:
            i = int(row["following_event_ID"])
            j = int(row["preceding_event_ID"])
            if verbose:
                print i,' follows ', j
            vtna.syllabus[i].precedingEvents.add(vtna.syllabus[j])
            vtna.syllabus[j].followingEvents.add(vtna.syllabus[i])
        if verbose:
            print "Events loaded"

        #Loop over planes
        cur.execute("SELECT * FROM plane WHERE active=TRUE")
        rows = cur.fetchall()
        for row in rows:
            # if verbose:
            #   print row["tail_number"],row["plane_type_ID"],row["max_cargo"]
            p =row["tail_number"]
            plane = Plane(id = p)
            plane.planetype = row["plane_type_ID"]
            ni = None
            tach = None
            if row["next_inspection"] != None:
                ni = float(row["next_inspection"])
            if row["tach"] != None:
                tach = float(row["tach"])
            if ni != None and tach != None and ni >= tach:
                plane.hours = ni-tach
            if ni != None and tach != None and ni < tach:
                plane.hours = 0.0
            if (row["max_cargo"]!= 0 and row["max_cargo"]!= None):
                plane.maxWeight = row["max_cargo"]
            if row["priority"] != None:
                plane.priority = row["priority"]
            vtna.planes[p]=plane

            #Add plane types

        #Add plane availability
        cur.execute("SELECT * FROM plane_unavail WHERE (end >= %s and start <= %s)",(vtna.schedules[1].day.strftime('%Y-%m-%d'),(vtna.schedules[vtna.days].day+timedelta(days=1)).strftime('%Y-%m-%d')))
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
            if verbose:
                print c
            inst = Instructor(id = c)
            inst.max_events = row["max_events"]
            if row["C990"]:
                inst.check = True
            if row["paid"]:
                inst.paid = 1

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
            stud = Student(id = s, squadron = vtna)
            stud.crewRestHours = 12
            # stud.crewRest = timedelta(hours=12)
            stud.syllabus = int(row["syllabus_ID"])
            if row["priority"] is not None:
                stud.priority = float(row["priority"])
            if row["last_flight"] is not None:
                stud.last_flight = row["last_flight"]
            cfi = row["onwing_CFI_ID"]
            if cfi in vtna.instructors:
                #if verbose: print "Add instructor",cfi
                stud.onwing = vtna.instructors[cfi]
            elif cfi != None:
                print 'CFI %d onwing for student %d not in instructors!'%(cfi,s)
            else:
                print 'no cfi for student %d'%(s)
            vtna.students[s] = stud
            # print vtna.students[s].__dict__
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
        cur.execute("SELECT * FROM sniv WHERE (end >= %s and start <= %s and approval=TRUE)",(vtna.schedules[1].day.strftime('%Y-%m-%d'),(vtna.schedules[vtna.days].day+timedelta(days=1)).strftime('%Y-%m-%d')))
        rows = cur.fetchall()
        i = 1
        for row in rows:
            id = row["user_ID"]
            if verbose:
                print id, row["start"], row["end"]
            s = Sniv(row)
            if id in vtna.students:
                vtna.students[id].snivs[i]=s
                i += 1
            elif id in vtna.instructors:
                vtna.instructors[id].snivs[i]=s
                i += 1

        if verbose:
            print "Snivs loaded"

        #Load most recent published schedule as schedule.today()
        cur.execute("SELECT * FROM schedule WHERE published=TRUE ORDER BY day DESC LIMIT 1")
        row = cur.fetchone()
        vtna.today.id = int(row["schedule_ID"])
        vtna.today.day = row["day"]
        midnight = datetime.combine(vtna.today.day, time(0))
        query = "SELECT * FROM schedule_wave WHERE schedule_ID = %d" % vtna.today.id
        cur.execute(query)
        rows = cur.fetchall()
        createWaves(vtna.today,rows,waves)
        query = "SELECT * FROM sortie WHERE schedule_ID = %s" % vtna.today.id
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            s = Sortie()
            id = int(row["sortie_ID"])
            if verbose:
                print id,row["CFI_ID"]
            s.brief = row["brief"]
            cfi_id = int(row["CFI_ID"])
            if cfi_id in vtna.instructors and row["wave_ID"] != None:
                s.instructor = vtna.instructors[cfi_id] #Instructor
                s.studentSorties = []
                s.takeoff = row["scheduled_takeoff"]
                s.land = row["scheduled_land"]
                if row["wave_ID"] in vtna.today.waves:
                    s.wave = vtna.today.waves[int(row["wave_ID"])] #Wave ojbect
                vtna.today.sorties[id]=s

        #Create sorties and studentSorties from the entries in those table corresponding to the most recent published sked
        cur.execute("SELECT * FROM student_sortie WHERE (status = 'pass' OR status = 'marginal' OR status = 'scheduled')")
        rows = cur.fetchall()
        for row in rows:
            if row["student_ID"] != None:
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
                        if row["plane_tail_number"] in vtna.planes:
                            sortie.plane = vtna.planes[row["plane_tail_number"]]
                        sortie.studentSorties.append(ss)
                        if vtna.today.day == (vtna.schedules[1].day-timedelta(days=1)):
                            #print "happy dance", stud.id, sortie.wave.id
                            takeoff = row["actual_takeoff"]
                            if not takeoff:
                                takeoff = midnight + sortie.takeoff
                            land = row["actual_land"]
                            if not land:
                                land = midnight + sortie.land
                            sniv = Sniv()
                            sniv.begin = takeoff
                            sniv.end = land + timedelta(hours=event.debrief_hours) + stud.crewRest()
                            stud.snivs[0]=sniv
                            instructor_sniv = Sniv()
                            instructor_sniv.begin = takeoff
                            instructor_sniv.end = land + timedelta(hours=event.debrief_hours) + sortie.instructor.crewRest()
                            sortie.instructor.snivs['crewrest' + str(row['student_sortie_ID'])] = instructor_sniv
            p = row["plane_tail_number"]
            if row["status"] == 'scheduled' and p in vtna.planes and row["sked_flight_hours"] != None:
                if (vtna.planes[p].hours - float(row["sked_flight_hours"])) >= 0:
                    vtna.planes[p].hours -= float(row["sked_flight_hours"])
                else:
                    vtna.planes[p].hours = 0.0



        """for s in vtna.students:
            stud = vtna.students[s]
            print 'Student: ', stud.id
            if stud.findPossible(1,True):
                print 'Next event: ', stud.getNextEvent()
            for event in stud.findPossible(1,True):
                if verbose:
                    print 'student ', s, 'possible event ', event.id"""


        #Loop over instructor preferences
        cur.execute("SELECT * FROM instructor_preference LEFT JOIN cfi ON instructor_preference.cfi_CFI_ID = cfi.CFI_ID WHERE cfi.active = TRUE")
        rows = cur.fetchall()
        for row in rows:
            c = int(row["cfi_CFI_ID"])
            pref = row["preference"]
            inst = vtna.instructors[c]
            begin = row["start"]
            end = row["end"]
            for d, sked in vtna.schedules.iteritems():
                midnight = datetime.combine(sked.day, time(0))
                start_time = midnight + begin
                end_time = midnight + end
                s = Sniv()
                s.begin = start_time
                s.end = end_time
                r = Instructor(id = 'sample')
                r.snivs[0] = s
                for w, wave in sked.waves.iteritems():
                    if not r.available(sked.day, wave):
                        inst.setPreference(d, w, pref)
                        if verbose:
                            print "Set preference for instructor %d, day %d, wave %d for value %d"%(c,d,w,pref)
    finally:
        con.close()



def createWaves(sked,rows,waves):
    for row in rows:
        i = int(row["wave_ID"])
        wave_entry = waves[i]
        #if verbose: print row["schedule_ID"],row["wave_ID"],row["priority"]
        w = Wave(i)
        #Plane times
        midnight = datetime.combine(sked.day,time(0))
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
        if wave_entry["student_multiple"] != None:
            w.studentMultiple = float(wave_entry["student_multiple"])
        sked.waves[i]=w
    sked.findExclusiveWaves()

def writeToDatabase(vtna,config):

    # con = mdb.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['db'])
    con = mysql.connector.connect(host=config['host'],port=config['port'],user=config['user'],passwd=config['password'],db=config['database'])

    try: # with con:
        # cur = con.cursor(mdb.cursors.DictCursor)
        cur = con.cursor(dictionary=True)

        for d in vtna.schedules:

            sked = vtna.schedules[d]
            day = sked.day

            cur.execute("SELECT * FROM schedule WHERE day=%(day)s AND published=0 LIMIT 1", {'day': day}) # .strftime('%Y-%m-%d %H-%M-%S') AND NOT flight_day = NULL
            row = cur.fetchone()
            """if rows == ():
                cur.execute("INSERT INTO schedule(day) VALUES(%s)",(day.strftime('%Y-%m-%d %H-%M-%S')))
                cur.execute("SELECT * FROM schedule WHERE day=%s",(day.strftime('%Y-%m-%d %H-%M-%S')))
                row = cur.fetchone()
                sked.id = row["schedule_ID"]
            else:"""
                #for row in rows:
            if row:
                sked.id = row["schedule_ID"]
                cur.execute("DELETE FROM student_sortie WHERE schedule_ID=%(schedule_ID)s", {'schedule_ID': sked.id})
                cur.execute("DELETE FROM sortie WHERE schedule_ID=%(schedule_ID)s", {'schedule_ID': sked.id})
                #Delete student sorties?

                for s in sked.sorties:
                    sortie = sked.sorties[s]
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
                    """if verbose:
                        print 'Sortie ID: ', sortie_id"""
                    for ss in sortie.studentSorties:
                        """if verbose:
                            print ss.student.id, ss.event.id"""
                        cur.execute("INSERT INTO student_sortie(schedule_ID,sortie_ID,student_ID,event_ID,sked_flight_hours,sked_inst_hours,plane_tail_number) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (sked.id,
                            sortie_id,
                            ss.student.id,
                            ss.event.id,
                            ss.event.flightHours,
                            ss.event.instructionalHours,
                            sortie.plane.id))
                print "Schedule for %s written to database"%(day)
    finally:
        con.commit()
        con.close()

if __name__ == '__main__':
    main()

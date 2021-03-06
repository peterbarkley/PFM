
#-------------------------------------------------------------------------------
# Name:        Watchbill Maker
# Purpose:
#
# Author:      pbarkley
#
# Created:     01/04/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import mysql.connector as mdb
import sys
from datetime import date, datetime, time, timedelta
from Squadron import Squadron
from Plane import Plane
from datetime import date, datetime, time, timedelta
from gurobipy import *
from Sniv import Sniv
from Resource import Resource
from Flyer import Flyer
from Instructor import Instructor
from Student import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Schedule import Schedule
from Wave import Wave
from Watch import Watch

verbose = True
period_pain = {10:2.7, 3:1.1, 4:1.0, 5:1.1, 7:1.3, 11:1.3}


class Watchbill(object):
    def __init__(self):
        self.today = Schedule()  # Current schedule
        self.schedules = {}  # Dictionary of schedules like {1:Schedule(date(2015,3,27)),2:Schedule(date...}
        self.tads = {}  # Dict w/ {user_ID: Resource(user_ID), ...}
        self.watches = {}
        self.m = Model()
        self.timeLimit = 360
        self.verbose = True
        self.vars = {}


def main():
    config = {}
    execfile(sys.argv[1], config)
    watchbill = Watchbill()
    watchbill.verbose = verbose
    if verbose:
        print "Loading model from database"
    load(watchbill, config)
    if verbose:
        print "Solving model"
    writeWatch(watchbill, config)
    #if verbose: print "Date loaded"


def load(vtna, config):

    con = mdb.connect(host=config['host'],
                      port=config['port'],
                      user=config['user'],
                      passwd=config['password'],
                      db=config['db'])

    cur = con.cursor(dictionary=True)

    #Loop over schedule table where not published and flight_day != NULL and add schedules for each flight_day
    cur.execute("SELECT * FROM schedule WHERE (published = FALSE) ORDER BY (day)") # AND NOT flight_day = NULL
    rows = cur.fetchall()
    i = 1
    for row in rows:
        # day = row["day"]
        sked = Schedule(row)
        # sked.id = int(row["schedule_ID"])
        # sked.blank = bool(row["blank"])

        if verbose:
            print 'Computing schedule for schedule ID %d'% (sked.id)
        vtna.schedules[i]=sked
        i += 1

    #Find watches
    for i in vtna.schedules:
        sked = vtna.schedules[i]
        sdo = Watch(1)
        sdo.name = 'SDO'
        sdou = Watch(2)
        sdou.name = 'SDO_UI'
        dd = Watch(3)
        dd.name = 'Duty_Driver'
        # trb_ensign = Watch(5)
        # trb_ensign.name = 'TRB_Ensign'
        """am_sdo = Sniv()
        am_sdo.begin = datetime.combine(sked.day,time(6))
        am_sdo.end = datetime.combine(sked.day,time(14))
        pm_sdo = Sniv()
        pm_sdo.begin = datetime.combine(sked.day,time(6))
        pm_sdo.end = datetime.combine(sked.day,time(14))
        sdo.periods[1] = am_sdo;
        sdo.periods[2] = pm_sdo;
        sdou.periods[1] = am_sdo
        sdou.periods[2] = pm_sdo"""
        sdo_period = Sniv()
        sdo_period.begin = datetime.combine(sked.day,time(6))
        sdo_period.end = datetime.combine(sked.day,time(21))
        sdo.periods[10] = sdo_period
        sdou.periods[10] = sdo_period
        am_dd = Sniv()
        mid_dd = Sniv()
        pm_dd = Sniv()
        am_dd.begin = datetime.combine(sked.day,time(5))
        am_dd.end = datetime.combine(sked.day,time(11))
        mid_dd.begin = datetime.combine(sked.day,time(10))
        mid_dd.end = datetime.combine(sked.day,time(17))
        pm_dd.begin = datetime.combine(sked.day,time(16))
        pm_dd.end = datetime.combine(sked.day,time(22))
        dd.periods[3]=am_dd
        dd.periods[4]=mid_dd
        dd.periods[5]=pm_dd
        sked.watches[1]=sdo
        sked.watches[2]=sdou
        sked.watches[3]=dd

    sdos = ['Segura', 'Lahey']
    dds = []
    quals = {1: sdos,  # SDOs
             2: sdos,
             3: dds}  # Duty Drivers

    # Loop over tads, adding them
    cur.execute("SELECT * FROM user WHERE role = 'tad'")
    rows = cur.fetchall()
    painpoints = {}
    for row in rows:
        s = int(row["user_ID"])
        if verbose:
            print 'User id ', s
        if s not in vtna.tads:
            t = Resource(id=s)
            t.name = (row["last_name"])
            vtna.tads[s] = t
        painpoints[s] = 0
        for watch_ID in quals:
            if t.name in quals[watch_ID]:
                vtna.tads[s].quals.append(watch_ID)

    cur.execute("SELECT watch_ID, watchstander_ID, watch_period_ID FROM watchbill LEFT JOIN schedule ON schedule.schedule_ID = watchbill.schedule_ID "
                "WHERE published = 1 AND YEAR = 2016 and watch_ID != 4")

    for row in cur.fetchall():
        painpoints[row["watchstander_ID"]] += period_pain[row["watch_period_ID"]]

    if verbose:
        print "TADs loaded"

    # Add snivs for students & CFIs
    cur.execute("SELECT * FROM sniv WHERE (end >= %(day)s and approval=TRUE)",
                {'day':vtna.schedules[1].day})
    rows = cur.fetchall()
    i=1
    for row in rows:
        id = row["user_ID"]
        if verbose:
            print id,row["start"],row["end"]
        if id in vtna.tads:
            s = Sniv()
            s.begin = row["start"]
            s.end = row["end"]
            vtna.tads[id].snivs[i]=s
            i = i+1

    if verbose:
        print "Snivs loaded"


def writeWatch(vtna, config):

    #Generate variables for each tad for each watch for each period
    objective = LinExpr()

    for d, sked in vtna.schedules.iteritems():
        for t, tad in vtna.tads.iteritems():
            for w, watch in sked.watches.iteritems():
                for p in watch.periods:
                    n = str(sked.day) + '_' + watch.name  + '_' + str(p) + '_ENS_'+ tad.name
                    vtna.vars[t,d,w,p] = vtna.m.addVar(vtype=GRB.BINARY,
                                                       name=n) #+1 to obj should be implied
    z = vtna.m.addVar(name='maxWatches')

    vtna.m.update()
    vtna.m.setObjective(z, GRB.MINIMIZE)
    #Generate constraints

    #Constraint 1: No watch when snivved
    for t, tad in vtna.tads.iteritems():
        for d, sked in vtna.schedules.iteritems():
            for w, watch in sked.watches.iteritems():
                for p, period in watch.periods.iteritems():
                    available = True
                    for s, sniv in tad.snivs.iteritems():
                        if sniv.end > period.begin and sniv.begin < period.end:
                            available = False
                    if not available:
                        vtna.m.addConstr(vtna.vars[t,d,w,p] == 0,
                                         '%s_snivved_during_%s_%d_%d' % (tad.name, watch.name, d, p))
                        if verbose:
                            print '%s_snivved_during_%s_%d_%d'%(tad.name,watch.name,d,p)

    # <= one watch per day for each tad
    for t, tad in vtna.tads.iteritems():
        for d, sked in vtna.schedules.iteritems():
            dayWatchSum = LinExpr()
            for w, watch in sked.watches.iteritems():
                for p, period in watch.periods.iteritems():
                    dayWatchSum.add(vtna.vars[t,d,w,p])
            vtna.m.addConstr(dayWatchSum<=1,'oneWatchPerDay_%s_%d'%(tad.name,d))
            if verbose:
                print 'oneWatchPerDay_%s_%d'%(tad.name,d)


    #time continuity: if scheduled during period p in day d, not schedule in period q!=p in day d+1
    for t, tad in vtna.tads.iteritems():
        for d, sked in vtna.schedules.iteritems():
            if(d != len(vtna.schedules)):
                for w, watch in sked.watches.iteritems():
                    for p, period in watch.periods.iteritems():
                        vtna.m.addConstr(vtna.vars[t,d,w,p] + quicksum(vtna.vars[t,d+1,u,q] for u in vtna.schedules[d+1].watches for q in vtna.schedules[d+1].watches[u].periods if q!=p) <= 1,  'continuity_%s_%s_%s_%d'%(tad.name,watch.name,d,p))

    # Stand 3 SDO U/I before SDO
    for t, tad in vtna.tads.iteritems():
        if 1 not in tad.quals:
            for d, sked in vtna.schedules.iteritems():
                vtna.m.addConstr(quicksum(vtna.vars[t,i,2,p]
                                          for i in range(1,d)
                                          for p in vtna.schedules[i].watches[2].periods)
                                 >= quicksum(vtna.vars[t,d,1,p]
                                             for p in sked.watches[1].periods), 'ui_%s_%d'%(tad.name,d))
                if verbose:
                    print 'ui_%s_%d'%(tad.name,d)

    # No watch for blank schedules
    for d, sked in vtna.schedules.iteritems():
        if sked.blank:
            vtna.m.addConstr(quicksum(vtna.vars[t,d,w,p] for t in vtna.tads for w in sked.watches for p in sked.watches[w].periods)==0,'blank_sked_%s'%(d))
            if verbose:
                print 'blank_sked_%s'%(d)

    # Fill all watches (except first three SDO)
    for d, sked in vtna.schedules.iteritems():
        if not sked.blank:
            for w, watch in sked.watches.iteritems():
                for p, period in watch.periods.iteritems():
                    if w != 2 and (sked.id > 262):
                        vtna.m.addConstr(quicksum(vtna.vars[t,d,w,p] for t in vtna.tads) == 1, 'fillWatch_%s_%s_%s'%(d,watch.name,p))
                        if verbose:
                            print 'fillWatch_%s_%s_%s'%(d,watch.name,p)

    # Work no more than 5 days in a row
    for t, tad in vtna.tads.iteritems():
        for d, sked in vtna.schedules.iteritems():
            if (d<len(vtna.schedules)-6):
                vtna.m.addConstr(quicksum(vtna.vars[t,i,w,p]
                                          for i in range(d,d+6)
                                          for w in sked.watches
                                          for p in sked.watches[w].periods) <= 5,
                                 'no_more_than_5_watches_in_a_row_%s_%s' % (d, t))

    # Stand SDO no more than once in three days
    for t, tad in vtna.tads.iteritems():
        for d, sked in vtna.schedules.iteritems():
            if d < len(vtna.schedules)-1:
                vtna.m.addConstr(quicksum(vtna.vars[t,i,1,10]
                                          for i in range(d,d+3)) <= 1,
                                 'no_more_than_1_sdo_in_three_days_%s_%s' % (d, t))

    """#Richline doesn't have driver's license
    for d, sked in vtna.schedules.iteritems():
        if sked.id < 31:
            w = 3
            watch = sked.watches[w]
            for p, period in watch.periods.iteritems():
                vtna.m.addConstr(vtna.vars[49,d,w,p]==0, 'richline_no_dd')
        w = 3
        watch = sked.watches[w]
        for p, period in watch.periods.iteritems():
            vtna.m.addConstr(vtna.vars[42,d,w,p]==0, 'khambahti_no_dd')"""

    scheduled = []
    #Set z as the maximum weighted watchstanding
    for t, tad in vtna.tads.iteritems():
        adjustment = 0
        if t in scheduled:
            adjustment = 1
        vtna.m.addConstr(z >= adjustment + quicksum(pain(t,vtna.schedules[d].day,p)*vtna.vars[t,d,w,p]
                                       for d in vtna.schedules
                                       for w in vtna.schedules[d].watches
                                       for p in vtna.schedules[d].watches[w].periods), 'pain_%s'%(tad.name))
        if verbose:
            print 'pain_%s'%(tad.name)


    vtna.m.params.timeLimit = vtna.timeLimit

    vtna.m.update()
    vtna.m.write('model.lp')
    vtna.m.optimize()
    model = vtna.m
    if model.status == GRB.status.INF_OR_UNBD:
        # Turn presolve off to determine whether model is infeasible
        # or unbounded
        model.setParam(GRB.param.presolve, 0)
        model.optimize()

    if model.status == GRB.status.OPTIMAL:
        print('Optimal objective: %g' % model.objVal)
        model.write('model.sol')
        if verbose:
            print "Writing model to database"
        writeToDatabase(vtna,config)
    elif model.status != GRB.status.INFEASIBLE:
        print('Optimization was stopped with status %d' % model.status)
        model.write('model.sol')
        if verbose:
            print "Writing model to database"
        writeToDatabase(vtna,config)
    else:
        # Model is infeasible - compute an Irreducible Inconsistent Subsystem (IIS)
        print('')
        print('Model is infeasible')
        model.computeIIS()
        model.write("model.ilp")
        print("IIS written to file 'model.ilp'")
    return True

def pain(t,d,p):
    day_pain = 1
    t_pain = 1
    if d.weekday() == 5:
        day_pain = 1.2
    if t == 35:
        t_pain = 50
    return period_pain[p]*day_pain*t_pain

def writeToDatabase(vtna,config):

    for v in vtna.m.getVars():
        if v.x == 1:
            print('%s %g' % (v.varName, v.x))

    for t, tad in vtna.tads.iteritems():
        print quicksum(pain(t, vtna.schedules[d].day, p)*vtna.vars[t,d,w,p].x
                       for d in vtna.schedules
                       for w in vtna.schedules[d].watches
                       for p in vtna.schedules[d].watches[w].periods)

    con = mdb.connect(host=config['host'],
                      port=config['port'],
                      user=config['user'],
                      passwd=config['password'],
                      db=config['db'])

    cur = con.cursor(dictionary=True)
    for d, sked in vtna.schedules.iteritems():
        day = sked.day
        id = sked.id
        cur.execute("DELETE FROM watchbill WHERE schedule_ID = %(id)s and watch_ID != 4", {'id':id})
        #cur.execute("SELECT * FROM schedule WHERE schedule_ID = %s",(id)) # AND NOT flight_day = NULL
        for w, watch in sked.watches.iteritems():
            for p, period in watch.periods.iteritems():
                for t in vtna.tads:
                    if vtna.vars[t,d,w,p].x == 1:
                        cur.execute("INSERT INTO watchbill (watch_ID, watchstander_ID, schedule_ID, watch_period_ID) "
                                    "VALUES (%(watch)s,%(tad)s,%(day)s,%(period)s)",
                        {'watch':w,
                        'tad':t,
                        'day':id,
                        'period':p})

    con.commit()
    return True

if __name__ == '__main__':
    main()

#-------------------------------------------------------------------------------
# Name:        Squadron
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from datetime import date, datetime, time, timedelta
from gurobipy import *
from Sniv import Sniv
from Flyer import Flyer
from Instructor import Instructor
from Odd import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Schedule import Schedule
from Wave import Wave
from sets import Set


class Squadron(object):
    """Meta object for scheduling program.
    Including lists of students, instructors, planes, and schedules, as well a syllabus of events for the students"""

    def __init__(self, *initial_data, **kwargs):
        self.planes = {} #Dictionary of plane objects like {'106RA': Plane('106RA'), ... }
        self.instructors = {}  #Dictionary of instructor objects like {9: Instructor(9), ... }
        self.students = {}  #Dictionary of student objects like {19: Student(19), ... }
        self.syllabus = {} #Dictionary of syllabus events like {-3: Event(-3), -2: Event(-2), ... }
        self.today = Schedule() #Current schedule object
        self.schedules = {} #Dictionary of schedules to be written like {1:Schedule(date(2015,3,27)),2:Schedule(date...}
        self.sevents = {} #Dictionary containing decision variables for all possible student sorties within date range
        self.ievents = {} #Dictionary containing decision variables for all possible instructor sorties within date range
        self.maintenance = {} #Dictionary of maintenance decision variables for plane p on day d like {(p,d,):Gurobi DV object, ... }
        self.m = Model() #Gurobi model
        self.days = 1
        self.timeLimit = 120
        self.verbose = True
        self.backToBack = False
        self.calculateMaintenance = False
        self.maxPlanesPerWave = 16
        self.sufficientTime = 0
        self.hardschedule = 0
        self.max_events = 2
        self.militaryPreference = 0
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    #Generates Waves in subsequent days that would be excluded by the crew rest requirements for a specific resource type
    #Returns a dictionary indexed by wave giving a list of the waves in the subsequent day that would be excluded b/c of crew rest for the resource type
    def generateCrewrestExclusion(self,day1,day2,resourceType):
        w={}
        if resourceType == "Student":
            s=Student(id="Sample", squadron=self)
        elif resourceType == "Instructor":
            s=Instructor(id="Sample")
        else:
            s=Flyer(id="Sample")
        for w1 in self.schedules[day1].waves:
            w[w1]=[]
            wave1=self.schedules[day1].waves[w1]
            rest=Sniv()
            rest.begin = wave1.times[resourceType].end
            rest.end = rest.begin + s.crewRest()
            s.snivs[0]=rest
            for w2 in self.schedules[day2].waves:
                wave2=self.schedules[day2].waves[w2]
                if not s.available(self.schedules[day2].day,wave2):
                    w[w1].append(w2)
        return w

    #This code constructs the Gurobi model, optimizes it, and outputs the results into the list of schedules
    #Probably want separate functions for each
    def writeSchedules(self):
        #Creates the Decision Variables for the model

        self.m = Model()
        self.createVariables()

        self.setStart()

        self.constructModel()

        self.m.params.timeLimit = self.timeLimit

        self.m.update()
        """m.params.simplexPricing = 3
        m.params.varBranch = 1
        m.params.cutPasses = 3
        m.params.tuneResults = 1
         Tune the model
        m.tune()
        if m.tuneResultCount > 0:
             Load the best tuned parameters into the model
            m.getTuneResult(0)
             Write tuned parameters to a file
            m.write('tune.prm')
        """
        # Solve the model using the tuned parameters
        """if True: # self.verbose:
            self.m.write('model.lp')"""
        self.m.optimize()

        model = self.m
        if model.status == GRB.status.INF_OR_UNBD:
            # Turn presolve off to determine whether model is infeasible
            # or unbounded
            model.setParam(GRB.param.presolve, 0)
            model.optimize()

        if model.status == GRB.status.OPTIMAL or model.status == GRB.status.TIME_LIMIT:
            print('Optimal objective: %g' % model.objVal)
            model.write('model.sol')
            self.outputModel()
            return True
        elif model.status != GRB.status.INFEASIBLE:
            print('Optimization was stopped with status %d' % model.status)
            model.write('model.sol')
            return False
        else:
            # Model is infeasible - compute an Irreducible Inconsistent Subsystem (IIS)
            print('')
            print('Model is infeasible')
            model.computeIIS()
            model.write("model.ilp")
            print("IIS written to file 'model.ilp'")
            return False


    #Creates the Decision Variables for the model
    def createVariables(self):
        #esd ={}
        studexpr = LinExpr()
        instexpr = LinExpr()
        objective = LinExpr()
        for d, sked in self.schedules.iteritems():
            #sked = self.schedules[d]
            day = sked.day
            for p in self.planes:
                plane = self.planes[p]
                if self.calculateMaintenance:
                    self.maintenance[p,d]=self.m.addVar(vtype=GRB.BINARY,name='maintenance_'+str(d)+'_'+str(p))
                for w in self.schedules[d].waves: #This is a dictionary key integer
                    wave = self.schedules[d].waves[w]
                    if plane.available(day,wave):
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane):
                                for event in stud.events(d,wave):
                                    #s: student id, plane: plane object, d: date object, w: schedule wave dictionary key, e: event object
                                    self.sevents[s,p,d,w,event.id]=self.m.addVar(vtype=GRB.BINARY,name='student_%s_event_%s_plane_%s_day_%s_wave_%s'%(s,event.id,p,d,w)) #+1 to obj should be implied
                                    objective.add(self.schedules[d].priority*wave.priority*stud.getPriority()*self.sevents[s,p,d,w,event.id])
                                    #studexpr.add(dcoeff[d]*wcoeff[w]*sprior[s]*sevents[s,p,d,w,e])
                                    if self.verbose:
                                        print "creating variable for student %s, plane %s, day %s, wave %s, event %s, multiplier %s"%(s,p,d,w,event.id, self.schedules[d].priority*wave.priority*stud.priority)
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane):
                                self.ievents[i,p,d,w]=self.m.addVar(vtype=GRB.BINARY,name='ievent_instructor_%s_plane_%s_on_day_%s_wave_%s'%(i,p,d,w))
                                prefCoefficient = inst.getPreference(d,w)
                                if self.militaryPreference and inst.paid:
                                    prefCoefficient = 0.1*prefCoefficient
                                objective.add((1+wave.planeHours()*(6-plane.priority)/40)*self.schedules[d].priority*prefCoefficient*self.ievents[i,p,d,w])
                                if self.verbose:
                                    print 'creating variable for instructor %s, plane %s, day %s, wave %s, multiplier %s'%(i,p,d,w,self.schedules[d].priority*wave.priority*inst.getPreference(d,w))

        self.m.update()
        self.m.setObjective(objective,GRB.MAXIMIZE)
        self.m.update()
        return 0

    #Update starting values
    def setStart(self):
        """for sortie_id in self.today.sorties:
            sortie = self.today.sorties[sortie_id]
            d=1
            day = self.schedules[d].day
            if sortie.studentSorties!=[] and self.schedules[d].waveNumber == self.today.waveNumber and sortie.plane != None:
                if sortie.plane.available(day,sortie.wave) and sortie.instructor.available(day,sortie.wave) and sortie.instructor.qualified(sortie.plane):
                        for ss in sortie.studentSorties:
                            s=ss.student
                            if s.available(day,sortie.wave) and s.qualified(sortie.plane):
                                #This should increment the events for subsequent days
                                self.ievents[sortie.instructor.id,sortie.plane.id,d,sortie.wave.id].start = 1.0
                                self.sevents[s.id,sortie.plane.id,d,sortie.wave.id,s.nextEvent.id].start = 1.0
                                #print str(s)+str(sortie.plane)+str(d)+str(sortie.wave)+str(s.nextEvent)

        self.m.update()"""
        return 0


    #This function should construct a model that meets all constraints and encompasses all requested schedules
    def constructModel(self):
        #Do not exceed hours remaining on aircraft
        if self.calculateMaintenance:
            for p, plane in self.planes.iteritems():
                plane_hours = LinExpr()
                for d, sked in self.schedules.iteritems():
                    daily_hours = LinExpr()
                    for w, wave in sked.waves.iteritems():
                        if plane.available(sked.day,wave):
                            for s, stud in self.students.iteritems():
                                if stud.qualified(plane):
                                    for event in stud.events(d,wave):
                                        plane_hours.add(event.flightHours * self.sevents[s,p,d,w,event.id])
                                        daily_hours.add(event.flightHours * self.sevents[s,p,d,w,event.id])
                    #Plane cannot fly while in maintenance
                    self.m.addConstr(daily_hours<=100*(1-self.maintenance[p,d]),
                    'no_flight_hours_while_in_maintenance_%s_%s'%(p,d)) #Constraint P1
                    if d>1:
                        self.m.addConstr(daily_hours<=100*(1-self.maintenance[p,d-1]),
                        'no_flight_hours_while_in_maintenance_%s_%s'%(p,d)) #Constraint P1
                    if d>2:
                        self.m.addConstr(daily_hours<=100*(1-self.maintenance[p,d-2]),
                        'no_flight_hours_while_in_maintenance_%s_%s'%(p,d)) #Constraint P1
                        self.m.addConstr(1-self.maintenance[p,d-2]>=self.maintenance[p,d-1]+self.maintenance[p,d],
                        'plane_%s_cannot_go_into_maintenace_for_two_days_if_it_goes_in_on_day_%s'%(p,d)) #Constraint P2
                    self.m.addConstr(plane_hours<=plane.hours+0.5+100*quicksum(self.maintenance[p,i] for i in self.schedules if i<d),
                    'on_day_%s_do_not_schedule_plane_%s_in_excess_of_100_total_hrs_per_inspection'%(d,p)) #Constraint P3
        else:
            #Don't exceed remaining plane hours
            for p, plane in self.planes.iteritems():
                self.m.addConstr(quicksum(self.sevents[stud.id,p,sked.flyDay,wave.id,event.id]*event.flightHours
                for sked in self.schedules.itervalues()
                for wave in self.schedules[sked.flyDay].waves.itervalues()
                for stud in self.students.itervalues()
                for event in stud.events(sked.flyDay,wave)
                if plane.available(sked.day,wave)
                and stud.qualified(plane)) <= plane.hours,'planeHours_%s'%(p)) #Constraint P3'

        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.day
            # Exclusive wave loop for planes
            for p, plane in self.planes.iteritems():
                for w in sked.exclusiveWaves["Plane"]:
                    wave1=sked.waves[w[0]]
                    wave2=sked.waves[w[1]]
                    expr = LinExpr()
                    for i, inst in self.instructors.iteritems():
                        if inst.qualified(plane) and plane.available(day,wave1) and plane.available(day,wave2):
                            expr.add(self.ievents[i,p,d,w[0]])
                            expr.add(self.ievents[i,p,d,w[1]])
                    self.m.addConstr(expr <=1,
                    'Do_not_schedule_plane_%s_on_day_%s_for_wave_%d_and_%d_because_they_overlap' % (p,d,w[0],w[1])) #Constraint P4

            for w in sked.waves:
                wave = sked.waves[w]
                #This restricts the number of planes in any particular wave if desired
                if sked.maxPlanesPerWave < 16:
                    self.m.addConstr(quicksum(self.ievents[i,p,d,w] for i in self.instructors for p in self.planes if (self.planes[p].available(day,wave) and self.instructors[i].qualified(self.planes[p]) ) ) <= sked.maxPlanesPerWave,
                    'Max_planes_per_wave_%s_%s' % (d,w))
                #This requires sufficient time for the flights to be completed
                if self.sufficientTime:
                    for p, plane in self.planes.iteritems():
                        if plane.available(day,wave):
                            self.m.addConstr(quicksum(event.flightHours*self.sevents[s,p,d,w,event.id] for s, stud in self.students.iteritems() for event in stud.events(d,wave) if stud.qualified(plane)) <= wave.planeHours(),
                            'Require_sufficient_time_in_wave_%s_day_%s_plane_%s_for_scheduled_events' % (w,d,p) ) #Constraint E1
                            if self.verbose:
                                print 'Events_fit_in_%s_hours for wave_%s_day_%s_plane_%s' % (wave.planeHours(),w,d,p)

                #This is the onePlanePerWave loop
                for i in self.instructors:
                    inst = self.instructors[i]
                    expr = LinExpr()
                    limit=1
                    text = 'instructor_%s_cannot_be_in_more_than_one_plane_on_day_%s_during_wave_%d'%(i,d,w)
                    if not inst.available(day,wave):
                        limit = 0
                        text = 'instructor_%s_not_available_on_day_%s_during_wave_%d'%(i,d,w)
                    for p in self.planes:
                        plane = self.planes[p]
                        if plane.available(day,wave) and inst.qualified(plane):
                            expr.add(self.ievents[i,p,d,w])
                    self.m.addConstr(expr<=limit, text) #Constraint I1

                for p in self.planes:
                    plane = self.planes[p]
                    if plane.available(day,wave):

                        #This is the oneInstPerPlane loop
                        expr = LinExpr()
                        maxWeightExpr = LinExpr()
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane):
                                    expr.add(self.ievents[i,p,d,w])
                                    maxWeightExpr.add(inst.weight*self.ievents[i,p,d,w])
                        self.m.addConstr(expr <= 1,
                        'Plane_%s_can_only_hold_one_instructor_on_day_%s_during_wave_%d' % (p,d,w)) #Constraint P5

                        #This is the student pairing loop
                        maxStudExpr = LinExpr()
                        maxStuds = len(self.students)
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane):
                                #This is the student pairing loop
                                if stud.partner!=None:
                                    if stud.partner.getNextEvent() == stud.getNextEvent():
                                        if self.verbose:
                                            print stud.id, stud.nextEvent, stud.partner.id, stud.partner.nextEvent
                                        for event in stud.events(d,wave):
                                            self.m.addConstr(self.sevents[s,p,d,wave.id,event.id]<=self.sevents[stud.partner.id,p,d,wave.id,event.id],
                                            'Students_%s_&_%s_are_partners_&_active_&_on_event_%s_if_one_flies_on_plane_%s_day_%d_wave_%s_the_other_must_as_well'% (s,stud.partner.id,event,p,d,wave.id)) #Constraint E2
                                #Max students constraint
                                for event in stud.events(d,wave):
                                    if self.verbose:
                                        print 'Event %d day %d wave %d maxstuds %d' % (event.id, d, w, event.max_students)
                                    maxStuds = min(maxStuds, event.max_students)
                                    maxStudExpr.add(self.sevents[s,p,d,w,event.id])
                                    if event.flightHours > 0.0:
                                        maxWeightExpr.add(stud.weight/wave.studentMultiple*self.sevents[s,p,d,w,event.id])
                        self.m.addConstr(maxStudExpr <= wave.studentMultiple*maxStuds,
                        'MaxStuds_%s_%s_%d' % (p,d,w)) #Constraint E1'
                        if self.verbose:
                            print 'Max studs is %d'%(maxStuds)
                        self.m.addConstr(maxWeightExpr <= plane.maxWeight,
                        'Limit_max_weight_for_plane_%s_on_day_%d_during_wave_%d' % (p,d,w)) #Constraint P6
                        #print 'Limit max weight for plane %s on day %d during wave %d' % (p,d,w)

            for i in self.instructors:
                inst = self.instructors[i]
                #Exclusive wave loop for instructors
                resourceType = "Flyer"
                if self.backToBack:
                    resourceType = "Plane"
                for w in sked.exclusiveWaves[resourceType]:
                    wave1=sked.waves[w[0]]
                    wave2=sked.waves[w[1]]
                    expr = LinExpr()
                    for p in self.planes:
                        plane = self.planes[p]
                        if inst.qualified(plane):
                            if plane.available(day,wave1):
                                expr.add(self.ievents[i,p,d,w[0]])
                            if plane.available(day,wave2):
                                expr.add(self.ievents[i,p,d,w[1]])
                    self.m.addConstr(expr <=1,
                    'Do_not_schedule_instructor_%s_on_day_%s_for_wave_%d_and_%d_because_they_overlap' % (i,d,w[0],w[1])) #Constraint I2
                if not self.backToBack:
                    #Don't fly an instructor more than their max events
                    maxEventExpr = LinExpr()
                    maxHoursExpr = LinExpr()
                    for w in sked.waves:
                        wave = sked.waves[w]
                        for p in self.planes:
                            plane = self.planes[p]
                            if inst.qualified(plane) and plane.available(day,wave):
                                maxEventExpr.add(self.ievents[i,p,d,w])
                                maxHoursExpr.add(self.ievents[i,p,d,w]*(wave.planeHours()-0.2))
                    self.m.addConstr(maxEventExpr <= inst.max_events, 'No_more_than_%d_events_for_instructor_%s_on_day_%s' % (inst.max_events,i,d)) # Constraint I3
                    self.m.addConstr(maxHoursExpr <= 8.0, 'No_more_than_8_flight_hours_for_instructor_%s_on_day_%s'%(i,d)) # Constraint I4

            #One event per day for students unless followsImmediately
            #Set onwing,offwing,check flight instructor requirements
            #Require a qualified instructor for all events
            for s in self.students:
                stud=self.students[s]
                #Optional constraint to require students to be scheduled
                if self.hardschedule and d==1 and stud.findPossible(d,True) != Set():
                    self.m.addConstr(quicksum(self.sevents[s,p,d,w,event.id] for p in self.planes for w, wave in sked.waves.iteritems() for event in stud.events(d,wave) if (stud.qualified(self.planes[p]) and self.planes[p].available(day,wave)) ) >= 1,
                    'Require_student_%s_to_be_scheduled'%(s)) #Constraint E3
                onePerDay = LinExpr()
                for w in sked.waves:
                    wave = sked.waves[w]
                    available = 1
                    availstring = 'student_available'
                    if not stud.available(day,wave):
                        available = 0
                        availstring = 'student_not_available'
                        self.m.addConstr(quicksum(self.sevents[s,p,d,w,event.id] for p,plane in self.planes.iteritems() for event in stud.events(d,wave) if (stud.qualified(plane) and plane.available(day,wave)))<=0,
                        'Student_%s_not_available_day_%s_wave_%s'%(s,d,w)) #Constraint S1
                    else:
                        for p in self.planes:
                            plane = self.planes[p]
                            if stud.qualified(plane) and plane.available(day,wave):
                                #  Should probably just calculate the eligible instructors in student or event object.
                                #  Problem is that it requires both.
                                for event in stud.events(d,wave):
                                    e=event.id
                                    if not event.followsImmediately:
                                        onePerDay.add(self.sevents[s,p,d,w,e])
                                    if event.onwing:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= self.ievents[stud.onwing.id,p,d,w],
                                        'student_%s_requires_onwing_%s_for_event_%s_plane_%s_day_%d_wave_%s'%(s, stud.onwing, event.id, p, d, w)) #Constraint E4
                                    elif event.offwing and not event.check:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].qualified(plane)),
                                        'student_%s_needs_offwing_for_event_%s_plane_%s_day_%s_wave_%d'%(s,event.id,p,d,w)) #Constraint E5
                                    elif not event.check:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if self.instructors[i].qualified(plane)),
                                        'Fly_With_Any_Inst_student_%s_plane_%s_day_%s_wave_%d'%(s,p,d,w)) #Constraint E7
                                    elif event.check:
                                        if not self.militaryPreference:
                                            if stud.onwing!=None:
                                                self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].check and self.instructors[i].qualified(plane)),
                                            'checkride_student_%s_plane_%s_day_%s_wave_%d'%(s,p,d,w)) #Constraint E6
                                            else:
                                                self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if self.instructors[i].check and self.instructors[i].qualified(plane)),
                                            'checkride_student_%s_plane_%s_day_%s_wave_%d'%(s,p,d,w)) #Constraint E6
                                        elif stud.onwing!=None:
                                            if stud.onwing.paid:
                                                self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if (i != stud.onwing.id and self.instructors[i].check and self.instructors[i].qualified(plane) and (not self.instructors[i].paid))),
                                            'checkride_student_%s_plane_%s_day_%s_wave_%d'%(s,p,d,w)) #Constraint E6
                                            else:
                                                self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].check and self.instructors[i].qualified(plane)),
                                            'checkride_student_%s_plane_%s_day_%s_wave_%d'%(s,p,d,w)) #Constraint E6
                                        else:
                                            self.m.addConstr(self.sevents[s,p,d,w,e] <= quicksum(self.ievents[i,p,d,w] for i in self.instructors if self.instructors[i].check and self.instructors[i].qualified(plane)),
                                            'checkride_student_%s_plane_%s_day_%s_wave_%d'%(s,p,d,w)) #Constraint E6

                self.m.addConstr(onePerDay <= 1, 'only_One_Event_for_student_%s_day_%s' % (s,d)) #Constraint E8

            #Student crew rest
            oneDay = timedelta(days=1)
            for subsequent in self.schedules:
                if(day+oneDay==self.schedules[subsequent].day):
                    w=self.generateCrewrestExclusion(d,subsequent,"Student")
                    for s in self.students:
                        stud = self.students[s]
                        for w1 in w:
                            wave1 = sked.waves[w1]
                            if w[w1]!=[]:
                                crewRestExpr=LinExpr()
                                for p in self.planes:
                                    plane = self.planes[p]
                                    if stud.qualified(plane):
                                        if plane.available(day,wave1):
                                            for event in stud.events(d,wave1):
                                                crewRestExpr.add(self.sevents[s,p,d,wave1.id,event.id])
                                        for w2 in w[w1]:
                                            wave2 = self.schedules[subsequent].waves[w2]
                                            if plane.available(subsequent,wave2):
                                                for event in stud.events(subsequent,wave2):
                                                    crewRestExpr.add(self.sevents[s,p,subsequent,wave2.id,event.id])
                                self.m.addConstr(crewRestExpr<=1,'CrewRest_student_%s_day_%s_wave_%d'%(s,d,w1)) #Constraint S2

        eventsOnce = {}
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.day
            for s in self.students:
                stud = self.students[s]
                for w in sked.waves:
                    wave = sked.waves[w]
                    for event in stud.events(d,wave):
                        if (s,event.id) not in eventsOnce:
                            eventsOnce[(s,event.id)]=LinExpr()
                        for p in self.planes:
                            plane = self.planes[p]
                            if stud.qualified(plane) and plane.available(day,wave):
                                eventsOnce[(s,event.id)].add(self.sevents[s,p,d,w,event.id])
        for k in eventsOnce:
            self.m.addConstr(eventsOnce[k]<=1,'Schedule_event_%d_once_for_student_%s'%(k[1],k[0])) #Constraint E9

        precedingEventsExpr = {}
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.day
            if d == 1:
                for s,stud in self.students.iteritems():
                    if self.verbose:
                        print 'Student %d'%(s)
                    for event in stud.findPossible(d,True):
                        if self.verbose:
                            print 'event %d'%(event.id)
                        for f in event.followingEvents:
                            if f.followsImmediately:
                                if self.verbose:
                                    print 'event %d'%(f.id)
                                for w, wave in sked.waves.iteritems():
                                    if self.verbose:
                                        print 'wave %d'%(w)
                                    if not wave.first():
                                        SameDayWavesExpr = LinExpr()
                                        for precedingw in wave.canImmediatelyFollow():
                                            if self.verbose:
                                                print ' preceding wave %d'%(precedingw)
                                            for p in self.planes:
                                                plane=self.planes[p]
                                                if stud.qualified(plane) and plane.available(d,sked.waves[precedingw]):
                                                    SameDayWavesExpr.add(self.sevents[s,p,d,precedingw,event.id])
                                        self.m.addConstr(SameDayWavesExpr>=quicksum(self.sevents[s,p,d,w,f.id] for p in self.planes if stud.qualified(self.planes[p]) and self.planes[p].available(d,wave)),
                                        'Schedule %s before scheduling immediately following %s on day %d during wave %d for student %s'%(event,f,d,w,s)) #Constraint E10
                                        if self.verbose:
                                            print 'Same Day Schedule %s before scheduling immediately following %s on day %d during wave %d for student %s'%(event,f,d,w,s)

            nextDay = d+1
            if d < self.days:
                for s in self.students:
                    #print 'Looping for day %d and student %s'%(d,s)
                    stud = self.students[s]
                    for event in stud.findPossible(d,False):
                        #print 'Prior event %s'%(event)
                        for f in event.followingEvents:
                            #print 'Following event %s'%(f)
                            followingEventExpr = LinExpr()
                            #Build off of the previous sum of that event for prior days if it has been found
                            if (s,d,f.id) in precedingEventsExpr:
                                precedingEventsExpr[(s,nextDay,f.id)]=precedingEventsExpr[(s,d,f.id)]
                            #If this is the first day it is available, begin constructing the sum over that event.
                            else:
                                precedingEventsExpr[(s,nextDay,f.id)]=LinExpr()
                            for w in sked.waves:
                                wave = sked.waves[w]
                                if event in stud.events(d,wave):
                                    for p in self.planes:
                                        plane=self.planes[p]
                                        if stud.qualified(plane) and plane.available(day,wave):
                                            #Add all the opportunitiese to fly that event on that day (to any already existing)
                                            precedingEventsExpr[(s,nextDay,f.id)].add(self.sevents[s,p,d,w,event.id])
                            for w in self.schedules[nextDay].waves:
                                wave = self.schedules[nextDay].waves[w]
                                for p in self.planes:
                                    plane=self.planes[p]
                                    if stud.qualified(plane) and plane.available(nextDay,wave):
                                        followingEventExpr.add(self.sevents[s,p,nextDay,w,f.id])
                                if f.followsImmediately:
                                    addedWavesExpr = LinExpr()
                                    for precedingw in wave.canImmediatelyFollow():
                                        for p in self.planes:
                                            plane=self.planes[p]
                                            if stud.qualified(plane) and plane.available(nextDay,self.schedules[nextDay].waves[precedingw]):
                                                addedWavesExpr.add(self.sevents[s,p,nextDay,precedingw,event.id])
                                    self.m.addConstr(precedingEventsExpr[(s,nextDay,f.id)]+addedWavesExpr>=quicksum(self.sevents[s,p,nextDay,w,f.id] for p in self.planes if stud.qualified(self.planes[p]) and plane.available(nextDay,wave)),
                                    'Schedule %s before scheduling immediately following %s on day %d during wave %d for student %s'%(event,f,nextDay,w,s)) #Constraint E10'
                                    #print '%s immediately follows %s'%(f,event)
                            if not f.followsImmediately:
                                #print '%s follows %s'%(f,event)
                                self.m.addConstr(precedingEventsExpr[(s,nextDay,f.id)]>=followingEventExpr,
                                'Schedule %s before scheduling %s on day %d for student %s'%(event,f,nextDay,s)) #Constraint E11
                                #print 'Schedule %s before scheduling %s on day %d for student %s'%(event,f,nextDay,s)

            for s in self.students:
                #print 'Looping for day %d and student %s'%(d,s)
                stud = self.students[s]
                for f in stud.findPossible(d,False):
                    if f.followsImmediately and f not in stud.findPossible(d,True):
                        for w in sked.waves:
                            wave = sked.waves[w]
                            if not wave.first():
                                addedWavesExpr = LinExpr()
                                for precedingw in wave.canImmediatelyFollow():
                                    for precedingEvent in f.precedingEvents:
                                        for p in self.planes:
                                            plane=self.planes[p]
                                            if stud.qualified(plane) and plane.available(day,sked.waves[precedingw]):
                                                addedWavesExpr.add(self.sevents[s,p,d,precedingw,precedingEvent.id])
                                self.m.addConstr(addedWavesExpr>=quicksum(self.sevents[s,p,d,w,f.id] for p in self.planes if stud.qualified(self.planes[p]) and self.planes[p].available(day,wave)),
                                'Schedule %s before scheduling immediately following %s on day %d during wave %d for student %s'%(precedingEvent,f,d,w,s)) #Constraint E10'
                                #print '%s immediately follows %s on day %d'%(f,precedingEvent,d)

        self.m.update()
        """
        print "Constraints"
        for c in self.m.getConstrs():
            print('%s' % c.constrName)
        """

    #This function should take the output of an optimized model and write it as sorties and student sorties into the correct flight schedule
    def outputModel(self):
        if self.calculateMaintenance:
            for i,v in self.maintenance.iteritems():
                if v.x == 1:
                    print('Perform maintenance on %s' % (v.varName))
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.day
            for p in self.planes:
                plane = self.planes[p]
                for w in self.schedules[d].waves: #This is a dictionary key integer
                    wave = self.schedules[d].waves[w]
                    if plane.available(day,wave):
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane) and self.ievents[i,p,d,w].x:
                                    sortie = Sortie()
                                    sortie.brief = wave.times["Flyer"].begin
                                    sortie.instructor = inst #Instructor object
                                    sortie.takeoff = wave.times["Plane"].begin
                                    sortie.land = wave.times["Plane"].end
                                    sortie.plane = plane #Plane object
                                    sortie.wave = wave #Wave ojbect
                                    sked.sorties[(p,w)]=sortie
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane):
                                for event in stud.events(d,wave):
                                    if self.sevents[s,p,d,w,event.id].x:
                                        ss = StudentSortie()
                                        ss.student = stud
                                        ss.event = event
                                        sked.sorties[(p,w)].studentSorties.append(ss)
        return True


def main():
    pass

if __name__ == '__main__':
    main()

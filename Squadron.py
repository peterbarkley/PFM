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
from Student import Student
from Event import Event
from Sortie import Sortie
from StudentSortie import StudentSortie
from Schedule import Schedule
from Wave import Wave


class Squadron(object):
    """Meta object for scheduling program. Including lists of students, instructors, planes, and schedules, as well a syllabus of events for the students"""

    def __init__(self):
        self.planes = {}
        self.instructors = {}
        self.students = {}
        self.syllabus = {} #Dictionary of syllabus events like {-3: Event(-3), -2: Event(-2), ... }
        self.today = Schedule(date.today()) #Current schedule
        self.schedules = {} #Dictionary of schedules to be written like {1:Schedule(date(2015,3,27)),2:Schedule(date...}
        self.sevents = {} #Dictionary containing decision variables for all possible student sorties within date range
        self.ievents = {} #Dictionary containing decision variables for all possible instructor sorties within date range
        self.maintenance = {}
        self.m = Model()
        self.totalFlightDays = 1
        self.timeLimit = 120
        self.verbose = True
        self.backToBack = False
        self.calculateMaintenance = False
        self.maxPlanesPerWave = 16

    #Returns the waves that a plane can fly on a given day
    def waves(self,day,wave,plane):
        #self.schedules[day]
        #How do I store this besides snivs?
        #It should have the flexibility to assign planes to specific waves if I break the staggers into specific waves
        #At the very least, it should query snivs for the planes on that day during that wave
        waves = self.schedules[day].waves #Should start as blank {}
        """for w in self.schedules[day].waves:
            if !self.planes[plane].snivved(w):
                waves.append(w)

        """
        return waves #This needs work

    #Generates Waves in subsequent days that would be excluded by the crew rest requirements for a specific resource type
    #Returns a dictionary indexed by wave giving a list of the waves in the subsequent day that would be excluded b/c of crew rest for the resource type
    def generateCrewrestExclusion(self,day1,day2,resourceType):
        w={}
        if resourceType=="Student":
            s=Student("Sample",self)
        elif resourceType=="Instructor":
            s=Instructor("Sample")
        else:
            s=Flyer("Sample")
        for w1 in self.schedules[day1].waves:
            w[w1]=[]
            wave1=self.schedules[day1].waves[w1]
            rest=Sniv()
            rest.begin = wave1.times[resourceType].end
            rest.end = rest.begin + s.crewRest
            s.snivs[0]=rest
            for w2 in self.schedules[day2].waves:
                wave2=self.schedules[day2].waves[w2]
                if not s.available(self.schedules[day2].date,wave2):
                    w[w1].append(w2)
        return w

    #This code constructs the Gurobi model, optimizes it, and outputs the results into the list of schedules
    #Probably want separate functions for each
    def writeSchedules(self):
        #Creates the Decision Variables for the model
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
            day = sked.date
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
                                    self.sevents[s,p,d,w,event.id]=self.m.addVar(vtype=GRB.BINARY,name='sevent_'+ str(d) + '_' + str(w) +'_'+ str(plane) +'_'+ str(stud) + '_' + str(event)) #+1 to obj should be implied
                                    objective.add((1+event.flightHours*plane.priority/20)*self.schedules[d].priority*wave.priority*stud.getPriority()*self.sevents[s,p,d,w,event.id])
                                    #studexpr.add(dcoeff[d]*wcoeff[w]*sprior[s]*sevents[s,p,d,w,e])
                                    if self.verbose:
                                        print "creating variable for student %s, plane %s, day %s, wave %s, event %s, multiplier %s"%(s,p,d,w,event.id, self.schedules[d].priority*wave.priority*stud.priority)
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane):
                                self.ievents[i,p,d,w]=self.m.addVar(vtype=GRB.BINARY,name='ievent_'+ str(d) + '_' + str(w) +'_'+ str(plane) +'_'+ str(inst))
                                objective.add(self.schedules[d].priority*inst.getPreference(d,w)*self.ievents[i,p,d,w])
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
            day = self.schedules[d].date
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
                        if plane.available(sked.date,wave):
                            for s, stud in self.students.iteritems():
                                if stud.qualified(plane):
                                    for event in stud.events(d,wave):
                                        plane_hours.add(event.flightHours * self.sevents[s,p,d,w,event.id])
                                        daily_hours.add(event.flightHours * self.sevents[s,p,d,w,event.id])
                    self.m.addConstr(daily_hours<=100*(1-self.maintenance[p,d]),'no_flight_hours_while_in_maintenance_%s_%s'%(p,d))
                    if d>1:
                        self.m.addConstr(daily_hours<=100*(1-self.maintenance[p,d-1]),'no_flight_hours_while_in_maintenance_%s_%s'%(p,d))
                    if d>2:
                        self.m.addConstr(daily_hours<=100*(1-self.maintenance[p,d-2]),'no_flight_hours_while_in_maintenance_%s_%s'%(p,d))
                        self.m.addConstr(1-self.maintenance[p,d-2]>=self.maintenance[p,d-1]+self.maintenance[p,d])
                    self.m.addConstr(plane_hours<=plane.hours+0.9+100*quicksum(self.maintenance[p,i] for i in self.schedules if i<d),'planeHours_%s_%s'%(p,d))
        else:
            for p, plane in self.planes.iteritems():
                self.m.addConstr(quicksum(self.sevents[stud.id,p,sked.flyDay,wave.id,event.id]*self.syllabus[event.id].flightHours
                for sked in self.schedules.itervalues()
                for wave in self.schedules[sked.flyDay].waves.itervalues()
                for stud in self.students.itervalues()
                for event in stud.events(sked.flyDay,wave)
                if plane.available(sked.date,wave)
                and stud.qualified(plane)) <= plane.hours,'planeHours_%s'%(p))

        #Don't exceed remaining plane hours
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.date
            #Exclusive wave loop for planes
            for p, plane in self.planes.iteritems():
                for w in sked.exclusiveWaves["Plane"]:
                    wave1=sked.waves[w[0]]
                    wave2=sked.waves[w[1]]
                    expr = LinExpr()
                    for i, inst in self.instructors.iteritems():
                        if inst.qualified(plane) and plane.available(day,wave1) and plane.available(day,wave2):
                            expr.add(self.ievents[i,p,d,w[0]])
                            expr.add(self.ievents[i,p,d,w[1]])
                    self.m.addConstr(expr <=1, 'Plane_No_Exclusive_Wave_%s_%s_%d_%d' % (p,d,w[0],w[1]))

            for w in sked.waves:
                wave = sked.waves[w]
                #This restricts the planes in any particular wave if desired
                if sked.maxPlanesPerWave < 16:
                    self.m.addConstr(quicksum(self.ievents[i,p,d,w] for i in self.instructors for p in self.planes if (self.planes[p].available(day,wave) and self.instructors[i].qualified(self.planes[p]) ) ) <= sked.maxPlanesPerWave,'Max_planes_per_wave_%s_%s' % (d,w))
                    for p, plane in self.planes.iteritems():
                        self.m.addConstr(quicksum(event.flightHours*self.sevents[s,p,d,w,event.id] for s, stud in self.students.iteritems() for event in stud.events(d,wave) if stud.qualified(plane)) <= wave.planeHours(),'Events_fit_in_wave_%s_day_%s_plane_%s' % (w,d,p) )

                #This is the onePlanePerWave loop
                for i in self.instructors:
                    inst = self.instructors[i]
                    expr = LinExpr()
                    limit=1
                    if not inst.available(day,wave):
                        limit = 0
                    for p in self.planes:
                        plane = self.planes[p]
                        if plane.available(day,wave) and inst.qualified(plane):
                            expr.add(self.ievents[i,p,d,w])
                    self.m.addConstr(expr<=limit,'onePlanePerWave_%s_%s_%d'%(i,d,w))

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
                        self.m.addConstr(expr <= 1, 'oneInstperPlane_%s_%s_%d' % (p,d,w))

                        #This is the student pairing loop
                        maxStudExpr = LinExpr()
                        maxStuds = len(self.students)
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane):
                                #This is the student pairing loop
                                if stud.partner!=None:
                                    if stud.partner.nextEvent == stud.nextEvent:
                                        for event in stud.events(d,wave):
                                            self.m.addConstr(self.sevents[s,p,d,w,event.id]<=self.sevents[stud.partner.id,p,d,w,event.id],
                                                        'OnWingsTogether_%s_%s_%s_%s_%d_%s'% (s,stud.partner.id,p,d,w,event))
                                #Max students constraint
                                for event in stud.events(d,wave):
                                    if self.verbose:
                                        print 'Event %d day %d wave %d maxstuds %d'%(event.id,d,w,event.maxStudents)
                                    maxStuds = min(maxStuds,event.maxStudents)
                                    maxStudExpr.add(self.sevents[s,p,d,w,event.id])
                                    if event.flightHours > 0.0:
                                        maxWeightExpr.add(stud.weight*self.sevents[s,p,d,w,event.id]/wave.studentMultiple)
                        self.m.addConstr(maxStudExpr <= wave.studentMultiple*maxStuds,'MaxStuds_%s_%s_%d' % (p,d,w))
                        if self.verbose:
                            print 'Max studs is %d'%(maxStuds)
                        self.m.addConstr(maxWeightExpr <= plane.maxWeight,'Limt max weight for plane %s on day %d during wave %d' % (p,d,w))
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
                        if inst.qualified(plane) and plane.available(day,wave1) and plane.available(day,wave2):
                            expr.add(self.ievents[i,p,d,w[0]])
                            expr.add(self.ievents[i,p,d,w[1]])
                    self.m.addConstr(expr <=1, 'Inst_No_Exclusive_Wave_%s_%s_%d_%d' % (i,d,w[0],w[1]))
                #Don't fly an instructor more than their max events
                maxEventExpr = LinExpr()
                for w in sked.waves:
                    wave = sked.waves[w]
                    for p in self.planes:
                        plane = self.planes[p]
                        if inst.qualified(plane) and plane.available(day,wave):
                            maxEventExpr.add(self.ievents[i,p,d,w])
                self.m.addConstr(maxEventExpr<= inst.maxEvents,'InstMaxEvents_%s_%s'%(i,d))

            #One event per day for students unless followsImmediately
            #Set onwing,offwing,check flight instructor requirements
            #Require a qualified instructor for all events
            for s in self.students:
                stud=self.students[s]
                onePerDay = LinExpr()
                for w in sked.waves:
                    wave = sked.waves[w]
                    available = 1
                    if not stud.available(day,wave):
                        available = 0
                    for p in self.planes:
                        plane = self.planes[p]
                        if stud.qualified(plane) and plane.available(day,wave):
                                for event in stud.events(d,wave):
                                    e=event.id
                                    if not event.followsImmediately:
                                        onePerDay.add(self.sevents[s,p,d,w,e])
                                    if event.onwing:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*self.ievents[stud.onwing.id,p,d,w],'withOnWing_%s_%s_%s_%s_%d_%s'%(s, stud.onwing, p, d, w, event))
                                    elif event.offwing and not event.check:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].qualified(plane)),
                                        'offwing_%s_%s_%s_%d'%(s,p,d,w))
                                    else:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if self.instructors[i].qualified(plane)),'FlyWithInst_%s_%s_%s_%d'%(s,p,d,w))
                                    if event.check:
                                        if stud.onwing!=None:
                                            self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].check and self.instructors[i].qualified(plane)),
                                        'check_%s_%s_%s_%d'%(s,p,d,w))
                                        else:
                                            self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if self.instructors[i].check and self.instructors[i].qualified(plane)),
                                        'check_%s_%s_%s_%d'%(s,p,d,w))
                self.m.addConstr(onePerDay <= 1, 'onlyOneEvent_%s_%s' % (s,d))

            #Student crew rest
            oneDay = timedelta(days=1)
            for subsequent in self.schedules:
                if(day+oneDay==self.schedules[subsequent].date):
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
                                self.m.addConstr(crewRestExpr<=1,'CrewRest_%s_%s_%d_to_%s'%(s,d,w1,subsequent))

        eventsOnce = {}
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.date
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
            self.m.addConstr(eventsOnce[k]<=1,'eventsScheduledOnce_%s_%d'%(k[0],k[1]))

        precedingEventsExpr = {}
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.date
            nextDay = d+1
            if d != self.totalFlightDays:
                for s in self.students:
                    #print 'Looping for day %d and student %s'%(d,s)
                    stud = self.students[s]
                    for event in stud.findPossible(d,False):
                        #print event
                        for f in event.followingEvents:
                            followingEventExpr = LinExpr()
                            if (s,d,f.id) in precedingEventsExpr:
                                precedingEventsExpr[(s,nextDay,f.id)]=precedingEventsExpr[(s,d,f.id)]
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
                                    'Schedule %s before scheduling immediately following %s on day %d during wave %d for student %s'%(event,f,nextDay,w,s))
                                    #print '%s immediately follows %s'%(f,event)
                            if not f.followsImmediately:
                                #print '%s follows %s'%(f,event)
                                self.m.addConstr(precedingEventsExpr[(s,nextDay,f.id)]>=followingEventExpr,'Schedule %s before scheduling %s on day %d for student %s'%(event,f,nextDay,s))

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
                                self.m.addConstr(addedWavesExpr>=quicksum(self.sevents[s,p,d,w,f.id] for p in self.planes if stud.qualified(self.planes[p]) and plane.available(day,wave)),
                                'Schedule %s before scheduling immediately following %s on day %d during wave %d for student %s'%(precedingEvent,f,d,w,s))
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
            day = sked.date
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

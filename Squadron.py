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


class Squadron(object):
    """Meta object for scheduling program. Including lists of students, instructors, planes, and schedules, as well a syllabus of events for the students"""

    def __init__(self):
        self.planes = {}
        self.instructors = {}
        self.students = {}
        self.syllabus = {} #Dictionary of syllabus events
        self.today = Schedule(date.today()) #Current schedule
        self.schedules = {} #Dictionary of schedules to be written like {date(2015,3,27):Schedule(date(2015,3,27))}
        self.sevents = {} #Dictionary containing decision variables for all possible student sorties within date range
        self.ievents = {} #Dictionary containing decision variables for all possible instructor sorties within date range
        self.m = Model()

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
                if not s.available(day2,wave2):
                    w[w1].append(w2)
        return w

    #This code constructs the Gurobi model, optimizes it, and outputs the results into the list of schedules
    #Probably want separate functions for each
    def writeSchedules(self):
        #Creates the Decision Variables for the model
        self.createVariables()

        self.setStart()

        self.constructModel()
        """
        m.params.timeLimit = 25

        m.update()
        m.params.simplexPricing = 3
        m.params.varBranch = 1
        m.params.cutPasses = 3
        #m.params.tuneResults = 1
        # Tune the model
        #m.tune()
        #if m.tuneResultCount > 0:
            # Load the best tuned parameters into the model
            #m.getTuneResult(0)
            # Write tuned parameters to a file
            #m.write('tune.prm')

        # Solve the model using the tuned parameters
        m.optimize()
        """
        return True


    #Creates the Decision Variables for the model
    def createVariables(self):
        #esd ={}
        studexpr = LinExpr()
        instexpr = LinExpr()
        objective = LinExpr()
        for d in self.schedules:
            for p in self.planes:
                plane = self.planes[p]
                for w in self.schedules[d].waves: #This is a dictionary key integer
                    wave = self.schedules[d].waves[w]
                    if plane.available(d,wave):
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane.planetype):
                                for event in stud.events(d,wave):
                                    #s: student id, plane: plane object, d: date object, w: schedule wave dictionary key, e: event object
                                    self.sevents[s,p,d,w,event.id]=self.m.addVar(vtype=GRB.BINARY,name='sevent_'+ str(d) + '_' + str(w) +'_'+ str(plane) +'_'+ str(stud) + '_' + str(event)) #+1 to obj should be implied
                                    objective.add(self.schedules[d].priority*wave.priority*stud.priority*self.sevents[s,p,d,w,event.id])
                                    #studexpr.add(dcoeff[d]*wcoeff[w]*sprior[s]*sevents[s,p,d,w,e])
                                    #print str(s)+str(p)+str(d)+str(w)+str(event)
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane.planetype):
                                self.ievents[i,p,d,w]=self.m.addVar(vtype=GRB.BINARY,name='ievent_'+ str(d) + '_' + str(w) +'_'+ str(plane) +'_'+ str(inst))
                                objective.add(inst.getPreference(d,w)*self.ievents[i,p,d,w])

        self.m.update()
        self.m.setObjective(objective,GRB.MAXIMIZE)
        self.m.update()
        return 0

    #Update starting values
    def setStart(self):
        for sortie in self.today.sorties:
            for d in self.schedules:
                if self.schedules[d].waveNumber == self.today.waveNumber:
                    if sortie.plane.available(d,sortie.wave) and sortie.instructor.available(d,sortie.wave):
                            for ss in sortie.studentSorties:
                                s=ss.student
                                if s.available(d,sortie.wave):
                                    #This should increment the events for subsequent days
                                    self.ievents[sortie.instructor.id,sortie.plane.id,d,sortie.wave.id].start = 1.0
                                    self.sevents[s.id,sortie.plane.id,d,sortie.wave.id,s.nextEvent.id].start = 1.0
                                    #print str(s)+str(sortie.plane)+str(d)+str(sortie.wave)+str(s.nextEvent)
        self.m.update()
        return 0


    #This function should construct a model that meets all constraints and encompasses all requested schedules
    def constructModel(self):
        for d in self.schedules:
            sked = self.schedules[d]
            for w in sked.waves:
                wave = sked.waves[w]
                #This is the onePlanePerWave loop
                for i in self.instructors:
                    inst = self.instructors[i]
                    expr = LinExpr()
                    limit=1
                    if not inst.available(d,wave):
                        limit = 0
                    for p in self.planes:
                        plane = self.planes[p]
                        if plane.available(d,wave) and inst.qualified(plane.planetype):
                            expr.add(self.ievents[i,p,d,w])
                    self.m.addConstr(expr<=limit,'onePlanePerWave_%s_%s_%d'%(i,d,w))

                for p in self.planes:
                    plane = self.planes[p]
                    if plane.available(d,wave):

                        #This is the oneInstPerPlane loop
                        expr = LinExpr()
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane.planetype):
                                    expr.add(self.ievents[i,p,d,w])
                        self.m.addConstr(expr <= 1, 'oneInstperPlane_%s_%s_%d' % (p,d,w))

                        #This is the student pairing loop
                        maxStudExpr = LinExpr()
                        maxStuds = len(self.students)
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane.planetype):
                                #This is the student pairing loop
                                if stud.partner!=None:
                                    if stud.partner.nextEvent == stud.nextEvent:
                                        for event in stud.events(d,wave):
                                            self.m.addConstr(self.sevents[s,p,d,w,event.id]<=self.sevents[stud.partner.id,p,d,w,event.id],
                                                        'OnWingsTogether_%s_%s_%s_%s_%d_%s'% (s,stud.partner.id,p,d,w,event))
                                #Max students constraint
                                for event in stud.events(d,wave):
                                    maxStuds = min(maxStuds,event.maxStudents)
                                    maxStudExpr.add(self.sevents[s,p,d,w,event.id])
                        self.m.addConstr(maxStudExpr <= wave.studentMultiple*maxStuds,'MaxStuds_%s_%s_%d' % (p,d,w))


            for i in self.instructors:
                inst = self.instructors[i]
                #Exclusive wave loop for instructors
                for w in sked.exclusiveWaves["Flyer"]:
                    wave1=sked.waves[w[0]]
                    wave2=sked.waves[w[1]]
                    expr = LinExpr()
                    for p in self.planes:
                        plane = self.planes[p]
                        if inst.qualified(plane.planetype) and plane.available(d,wave1) and plane.available(d,wave2):
                            expr.add(self.ievents[i,p,d,w[0]])
                            expr.add(self.ievents[i,p,d,w[1]])
                    self.m.addConstr(expr <=1, 'Inst_No_Exclusive_Wave_%s_%s_%d_%d' % (i,d,w[0],w[1]))
                #Don't fly an instructor more than their max events
                maxEventExpr = LinExpr()
                for w in sked.waves:
                    wave = sked.waves[w]
                    for p in self.planes:
                        plane = self.planes[p]
                        if inst.qualified(plane.planetype) and plane.available(d,wave):
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
                    if not stud.available(d,wave):
                        available = 0
                    for p in self.planes:
                        plane = self.planes[p]
                        if stud.qualified(plane.planetype) and plane.available(d,wave):
                                for event in stud.events(d,wave):
                                    e=event.id
                                    if not event.followsImmediately:
                                        onePerDay.add(self.sevents[s,p,d,w,e])
                                    if event.onwing:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*self.ievents[stud.onwing.id,p,d,w],'withOnWing_%s_%s_%s_%s_%d_%s'%(s, stud.onwing, p, d, w, event))
                                    elif event.offwing and not event.check:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].qualified(plane.planetype)),
                                        'offwing_%s_%s_%s_%d'%(s,p,d,w))
                                    else:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if self.instructors[i].qualified(plane.planetype)),'FlyWithInst_%s_%s_%s_%d'%(s,p,d,w))
                                    if event.check:
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].check and self.instructors[i].qualified(plane.planetype)),
                                        'check_%s_%s_%s_%d'%(s,p,d,w))
                self.m.addConstr(onePerDay <= 1, 'onlyOneEvent_%s_%s' % (s,d))

            #Student crew rest
            oneDay = timedelta(days=1)
            for subsequent in self.schedules:
                if(d+oneDay==subsequent):
                    w=self.generateCrewrestExclusion(d,subsequent,"Student")
                    for s in self.students:
                        stud = self.students[s]
                        for w1 in w:
                            wave1 = sked.waves[w1]
                            if w[w1]!=[]:
                                crewRestExpr=LinExpr()
                                for p in self.planes:
                                    plane = self.planes[p]
                                    if stud.qualified(plane.planetype):
                                        if plane.available(d,wave1):
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
            for s in self.students:
                stud = self.students[s]
                for w in sked.waves:
                    wave = sked.waves[w]
                    for event in stud.events(d,wave):
                        if (s,event.id) not in eventsOnce:
                            eventsOnce[(s,event.id)]=LinExpr()
                        for p in self.planes:
                            plane = self.planes[p]
                            if stud.qualified(plane.planetype) and plane.available(d,wave):
                                eventsOnce[(s,event.id)].add(self.sevents[s,p,d,w,event.id])
        for k in eventsOnce:
            self.m.addConstr(eventsOnce[k]<=1,'eventsScheduledOnce_%s_%d'%(k[0],k[1]))


            #ne = stud.nextEvent.id
            #for event in range(ne,)
        """
         #Each event is only scheduled once
        for s in studs:
            for e in events:
                if e >= syll[s]:
                    expr = LinExpr()
                    for d in days:
                        if e<syll[s]+d:
                            for w in waves:
                                for p in planes:
                                    if squal[s,p]==1 and pavail[p,d,w]==1:
                                        expr.add(sevents[s,p,d,w,e])
                        else:
                            if e==10 and e==syll[s]+d:
                                for w in waves:
                                    for p in planes:
                                        if squal[s,p]==1 and pavail[p,d,w]==1:
                                            expr.add(sevents[s,p,d,w,e])
                    m.addConstr(expr<=1,'eventsScheduledOnce_%s_%d'%(s,e))
        """
        self.m.update()
        print "Constraints"
        for c in self.m.getConstrs():
            print('%s' % c.constrName)
        """



               #Each plane should have <= 2 students per block



        #Events G1-C990 must be sequentially scheduled at least the day before
        eventpairs = events[:]
        del eventpairs[-1]
        del eventpairs[-1]
        for s in studs:
            for e in eventpairs:
                for d in daypairs:
                    if e>=syll[s] and e<syll[s]+d:
                        expr1 = LinExpr()
                        expr2 = LinExpr()
                        for p in planes:
                            if squal[s,p]==1:
                                for d1 in range(1,d):
                                    if d1>e-syll[s]:
                                        for w in waves:
                                            if pavail[p,d1,w]:
                                                expr1.add(sevents[s,p,d1,w,e])
                                for w in waves:
                                    if pavail[p,d+1,w]:
                                        expr2.add(sevents[s,p,d+1,w,e+1])
                        #m.addConstr(expr1-expr2>=0,'sequentialEvents_%s_event_%d_day_%d'%(s,e,d))
                        m.addConstr(quicksum(sevents[s,p,d1,w,e] for p in planes for d1 in days for w in waves if squal[s,p]==1 and d1<=d and d1>e-syll[s] and pavail[p,d1,w])-quicksum(sevents[s,p,d+1,w,e+1] for p in planes for w in waves if squal[s,p]==1 and pavail[p,d+1,w])>=0,                                'sequentialEvents_%s_event_%d_day_%d'%(s,e,d))

        #C990 in a wave before C10
        e = 9
        for s in studs:
            for d in days:
                if e>=syll[s] and e<syll[s]+d:
                    for w in [1,2,3,4,5]:
                        expr = LinExpr()
                        for d1 in range(1,d+1):
                            if e>=syll[s] and e<syll[s]+d1:
                                if d1==d:
                                    for w1 in range(1,w):
                                        for p in planes:
                                            if squal[s,p]==1 and pavail[p,d1,w1]:
                                                expr.add(sevents[s,p,d1,w1,e])
                                else:
                                    for w1 in waves:
                                        for p in planes:
                                            if squal[s,p]==1 and pavail[p,d1,w1]:
                                                expr.add(sevents[s,p,d1,w1,e])
                        soloexpr = LinExpr()
                        for p in planes:
                            if squal[s,p]==1 and pavail[p,d,w]:
                                soloexpr.add(sevents[s,p,d,w,e+1])
                        m.addConstr(expr-soloexpr>=0,'c990beforec10_%s_%d_%d'%(s,d,w))


        #Max plane weight
        #maxweight = 600
        if limitweight:
            for p in planes:
                for d in days:
                    for w in waves:
                        if pavail[p,d,w]:
                            expr = LinExpr()
                            for s in studs:
                                if squal[s,p]==1:
                                    for e in events:
                                        if e>=syll[s]:
                                            if e<syll[s]+d:
                                                expr.add(sweight[s]*sevents[s,p,d,w,e])
                                            else:
                                                if e==10 and e==syll[s]+d:
                                                    expr.add(sweight[s]*sevents[s,p,d,w,e])
                            for i in insts:
                                if iqual[i,p]==1:
                                    expr.add(iweight[i]*ievents[i,p,d,w])
                            m.addConstr(expr<=maxweight,'maxWeight_%s_%d_%d' % (p,d,w))
                            """

    #This function should take the output of an optimized model and write it as sorties and student sorties into the correct flight schedule
    def outputModel(self):
        return True


def main():
    pass

if __name__ == '__main__':
    main()

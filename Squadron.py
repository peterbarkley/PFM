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
        self.syllabus = {} #Dictionary of syllabus events
        self.today = Schedule(date.today()) #Current schedule
        self.schedules = {} #Dictionary of schedules to be written like {1:Schedule(date(2015,3,27)),2:Schedule(date...}
        self.sevents = {} #Dictionary containing decision variables for all possible student sorties within date range
        self.ievents = {} #Dictionary containing decision variables for all possible instructor sorties within date range
        self.m = Model()
        self.totalFlightDays = 1
        self.timeLimit = 30

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
        self.outputModel()
        return True


    #Creates the Decision Variables for the model
    def createVariables(self):
        #esd ={}
        studexpr = LinExpr()
        instexpr = LinExpr()
        objective = LinExpr()
        for d in self.schedules:
            sked = self.schedules[d]
            day = sked.date
            for p in self.planes:
                plane = self.planes[p]
                for w in self.schedules[d].waves: #This is a dictionary key integer
                    wave = self.schedules[d].waves[w]
                    if plane.available(day,wave):
                        for s in self.students:
                            stud = self.students[s]
                            if stud.qualified(plane):
                                for event in stud.events(d,wave):
                                    #s: student id, plane: plane object, d: date object, w: schedule wave dictionary key, e: event object
                                    self.sevents[s,p,d,w,event.id]=self.m.addVar(vtype=GRB.BINARY,name='sevent_'+ str(d) + '_' + str(w) +'_'+ str(plane) +'_'+ str(stud) + '_' + str(event)) #+1 to obj should be implied
                                    objective.add(self.schedules[d].priority*wave.priority*stud.priority*self.sevents[s,p,d,w,event.id])
                                    #studexpr.add(dcoeff[d]*wcoeff[w]*sprior[s]*sevents[s,p,d,w,e])
                                    #print s,p,d,w,event.id
                        for i in self.instructors:
                            inst = self.instructors[i]
                            if inst.qualified(plane):
                                self.ievents[i,p,d,w]=self.m.addVar(vtype=GRB.BINARY,name='ievent_'+ str(d) + '_' + str(w) +'_'+ str(plane) +'_'+ str(inst))
                                objective.add(inst.getPreference(d,w)*self.ievents[i,p,d,w])
                                #print i,p,d,w

        self.m.update()
        self.m.setObjective(objective,GRB.MAXIMIZE)
        self.m.update()
        return 0

    #Update starting values
    def setStart(self):
        for sortie in self.today.sorties:
            for d in self.schedules:
                day = self.schedules[d].date
                if self.schedules[d].waveNumber == self.today.waveNumber:
                    if sortie.plane.available(day,sortie.wave) and sortie.instructor.available(day,sortie.wave):
                            for ss in sortie.studentSorties:
                                s=ss.student
                                if s.available(day,sortie.wave):
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
            day = sked.date
            for w in sked.waves:
                wave = sked.waves[w]
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
                                    maxStuds = min(maxStuds,event.maxStudents)
                                    maxStudExpr.add(self.sevents[s,p,d,w,event.id])
                                    maxWeightExpr.add(stud.weight*self.sevents[s,p,d,w,event.id])
                        self.m.addConstr(maxStudExpr <= wave.studentMultiple*maxStuds,'MaxStuds_%s_%s_%d' % (p,d,w))
                        self.m.addConstr(maxWeightExpr <= plane.maxWeight/wave.studentMultiple,'Limt max weight for plane %s on day %d during wave %d' % (p,d,w))
                        #print 'Limit max weight for plane %s on day %d during wave %d' % (p,d,w)


            for i in self.instructors:
                inst = self.instructors[i]
                #Exclusive wave loop for instructors
                for w in sked.exclusiveWaves["Flyer"]:
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
                                        self.m.addConstr(self.sevents[s,p,d,w,e] <= available*quicksum(self.ievents[i,p,d,w] for i in self.instructors if i != stud.onwing.id and self.instructors[i].check and self.instructors[i].qualified(plane)),
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
        for v in self.m.getVars():
            if v.x == 1:
                print('%s %g' % (v.varName, v.x))
        return True


def main():
    pass

if __name__ == '__main__':
    main()

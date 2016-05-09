#-------------------------------------------------------------------------------
# Name:        JSSO
# Purpose:
#
# Author:      pbarkley
#
# Created:     8/2/2016
# Copyright:   (c) pbarkley 2016
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
from sets import Set


class JobShop(object):
    """Meta object for scheduling program. Including lists of students, instructors, planes, and schedules, as well a syllabus of events for the students"""

    def __init__(self):
        self.planes = {} #Dictionary of plane objects like {'106RA': Plane('106RA'), ... }
        self.instructors = {}  #Dictionary of instructor objects like {9: Instructor(9), ... }
        self.students = {}  #Dictionary of student objects like {19: Student(19), ... }
        self.syllabus = {} #Dictionary of syllabus events like {-3: Event(-3), -2: Event(-2), ... }
        self.today = Schedule(date.today()) #Current schedule object
        self.schedules = {} #Dictionary of schedules to be written like {1:Schedule(date(2015,3,27)),2:Schedule(date...}
        self.pevents = {} #Dictionary containing decision variables for all possible student sortie plane assignments
        self.ievents = {} #Dictionary containing decision variables for all possible student sortie instructor assignments
        self.starts = {}
        self.completes = {}
        self.before = {}
        self.together = {}
        self.maintenance = {} #Dictionary of maintenance decision variables for plane p on day d like {(p,d,):Gurobi DV object, ... }
        self.m = Model() #Gurobi model
        self.totalFlightDays = 1
        self.timeLimit = 120
        self.verbose = True
        self.backToBack = False
        self.calculateMaintenance = False
        self.maxPlanesPerWave = 16
        self.sufficientTime = 0
        self.hardschedule = 0
        self.militaryPreference = 0

    #Generates Waves in subsequent days that would be excluded by the crew rest requirements for a specific resource type
    #Returns a dictionary indexed by wave giving a list of the waves in the subsequent day that would be excluded b/c of crew rest for the resource type
    def generateCrewrestExclusion(self, day1, day2, resourceType):
        w = {}
        if resourceType == "Student":
            s = Student("Sample", self)
        elif resourceType == "Instructor":
            s = Instructor("Sample")
        else:
            s = Flyer("Sample")
        for w1 in self.schedules[day1].waves:
            w[w1] = []
            wave1 = self.schedules[day1].waves[w1]
            rest = Sniv()
            rest.begin = wave1.times[resourceType].end
            rest.end = rest.begin + s.crewRest
            s.snivs[0] = rest
            for w2 in self.schedules[day2].waves:
                wave2 = self.schedules[day2].waves[w2]
                if not s.available(self.schedules[day2].date,wave2):
                    w[w1].append(w2)
        return w

    #This code constructs the Gurobi model, optimizes it, and outputs the results into the list of schedules
    #Probably want separate functions for each
    def writeSchedules(self):
        #Creates the Decision Variables for the model

        self.m = Model()
        self.createVariables()

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

    def crewrest(self):
        crewrest = set()
        for day in self.schedules:
            crewrest.add('cr_%s' % (day))
        return crewrest


    #Creates the Decision Variables for the model
    def createVariables(self):
        d = len(self.schedules)
        objective = LinExpr()
        for s, stud in self.students.iteritems():
            events = stud.findPossible(d,False)
            for event in events:
                ss = StudentSortie(stud, event)
                for i, instructor in self.instructors.iteritems():
                    sortie = Sortie(instructor)
                    sortie.studentSorties.append(ss)
                    if sortie.feasible():
                        # Add instructor event assignments
                        self.ievents[i,s,event.id] = self.m.addVar(vtype = GRB.BINARY,
                                                                 name = 'instructor_%s_student_%s_event_%s' % (i, s, event.id))
                        if self.verbose:
                            print 'instructor_%s_student_%s_event_%s' % (i, s, event.id)
                        for day in self.schedules:
                            self.before[s,event.id,i,'cr_%s'%(day)] = self.m.addVar(vtype = GRB.BINARY,
                                                                          name = 'student_%s_event_%s_before_instructor_%s_crewrest_%s'
                                                                          % (s, event.id, i, day))
                            self.before[i,'cr_%s'%(day),s,event.id] = self.m.addVar(vtype = GRB.BINARY,
                                                                          name = 'instructor_%s_crewrest_%s_before_student_%s_event_%s'
                                                                          % (i, day, s, event.id))
                for p, plane in self.planes.iteritems():
                    sortie = Sortie(None,plane)
                    sortie.studentSorties.append(ss)
                    if sortie.feasible():
                        # Add plane event assignments
                        self.pevents[p, s, event.id] = self.m.addVar(vtype = GRB.BINARY,
                                                                     name = 'plane_%s_student_%s_event_%s' % (p, s, event.id))
                        objective.add(self.pevents[p, s, event.id])
                        if self.verbose:
                            print 'plane_%s_student_%s_event_%s' % (p, s, event.id)
                self.starts[s, event.id] = self.m.addVar(lb = 0,
                                                        name = 'start_time_for_student_%s_event_%s' % (s, event.id))
                if self.verbose:
                    print 'start_time_for_student_%s_event_%s' % (s, event.id)
                self.completes[s, event.id] = self.m.addVar(lb = 0,
                                                        name = 'completion_time_for_student_%s_event_%s' % (s, event.id))
                objective.add(-0.001 * self.completes[s, event.id])
                if self.verbose:
                    print 'completion_time_for_student_%s_event_%s' % (s, event.id)
                for s2, stud2 in self.students.iteritems():
                    if s2 != s:
                        for event2 in stud2.findPossible(d, False):
                            self.before[s,event.id,s2,event2.id] = self.m.addVar(vtype = GRB.BINARY,
                                                                                 name = 'student_%s_event_%s_before_student_%s_event_%s'
                                                                                 % (s, event.id, s2, event2.id))
                            if self.verbose:
                                print 'student_%s_event_%s_before_student_%s_event_%s' % (s, event.id, s2, event2.id)
                            # if s < s2 and (s, s2, event.id, event2.id) not in self.together:
                            self.together[s, s2, event.id, event2.id] = self.m.addVar(vtype = GRB.BINARY,
                                                                                   name = 'students_%s_and_%s_together_for_events_%s_and_%s'
                                                                                   % (s, s2, event.id, event2.id))
                            if self.verbose:
                                print 'students_%s_and_%s_together_for_events_%s_and_%s' % (s, s2, event.id, event2.id)

                for d in self.schedules:
                    self.before[s, event.id, s, 'cr_%s' % (d)] = self.m.addVar(vtype = GRB.BINARY,
                                                                             name = 'student_%s_event_%s_before_student_%s_crewrest_%s'
                                                                             % (s, event.id, s, d))
                    self.before[s, 'cr_%s' % (d), s, event.id] = self.m.addVar(vtype = GRB.BINARY,
                                                                             name = 'student_%s_crewrest_%s_before_student_%s_event_%s'
                                                                             % (s, d, s, event.id))
            # Add student crew rest events
            for d in self.schedules:
                self.starts[s, 'cr_%s' % (d)] = self.m.addVar(lb = 0, name = 'start_student_%s_crewrest_%s' % (s, d))
                self.completes[s, 'cr_%s' % (d)] = self.m.addVar(lb = 0, name = 'complete_student_%s_crewrest_%s' % (s, d))

            # Add student snivs
        # Add instructor crew rest events
        for i, instructor in self.instructors.iteritems():
            for d in self.schedules:
                self.starts[i, 'cr_%s' % (d)] = self.m.addVar(lb = 0, name = 'start_instructor_%s_crewrest_%s' % (i, d))
                self.completes[i, 'cr_%s' % (d)] = self.m.addVar(lb = 0, name = 'complete_instructor_%s_crewrest_%s' % (i, d))
                if self.verbose:
                    print 'instructor_%s_crewrest_event_%s' % (i, d)
        self.m.update()
        self.m.setObjective(objective, GRB.MAXIMIZE)
        self.m.update()
        return 0

    #This function should construct a model that meets all constraints and encompasses all requested schedules
    def constructModel(self):
        # Event is complete after all event time is spent
        d = len(self.schedules)
        for s, stud in self.students.iteritems():
            events = stud.findPossible(d, False)
            for event in events:
                ss = StudentSortie(stud, event)
                e = event.id
                self.m.addConstr(self.starts[s,event.id] + event.flightHours + event.instructionalHours + event.planeHours
                                 + quicksum((event2.flightHours + event2.planeHours)*self.together[s, s2, e, event2.id]
                                            for s2, stud2 in self.students.iteritems() if s2 != s
                                            for event2 in stud2.findPossible(d, False))
                                 == self.completes[s, e],
                                 'Student_%s_event_%s_includes_enough_time_for_event_and_partners'
                                 % (s, e))
                # self.m.addConstr(quicksum(event.flightHours*self.sevents[s,p,d,w,event.id] for s, stud in self.students.iteritems() for event in stud.events(d,wave) if stud.qualified(plane)) <= wave.planeHours(),
                # 'Require_sufficient_time_in_wave_%s_day_%s_plane_%s_for_scheduled_events' % (w,d,p) ) #Constraint E1
                # Schedule each event on no more than one plane
                self.m.addConstr(quicksum(self.pevents[p, s, e] for p in self.planes if self.pevents[p, s, e]) <= 1,
                                 'schedule_student_%s_event_%s_with_no_more_than_one_plane'
                                 % (s, event.id))

                # Schedule each event on no more than one instructor
                self.m.addConstr(quicksum(self.ievents[i, s, e] for i in self.instructors if ((i, s, e) in self.ievents)) <= 1,
                                 'schedule_student_%s_event_%s_with_no_more_than_one_instructor'
                                 % (s, event.id))

                # Scheduled planes = scheduled instructors
                self.m.addConstr(quicksum(self.ievents[i, s, e] for i in self.instructors if ((i, s, e) in self.ievents)) ==
                                 quicksum(self.pevents[p, s, e] for p in self.planes if ((p, s, e) in self.pevents)),
                                 'schedule_student_%s_event_%s_with_same_number_of_planes_and_instructors'
                                 % (s, event.id))
                for s2, stud2 in self.students.iteritems():
                    if s2 != s:
                        for event2 in stud2.findPossible(d, False):
                            ss2 = StudentSortie(stud2, event2)
                            # s1 before s2 or s2 before s1
                            self.m.addConstr(self.before[s, event.id, s2, event2.id]
                                             + self.before[s2, event2.id, s, event.id]
                                             + self.together[s, s2, e, event2.id]
                                             == 1,
                                             'student_%s_event_%s_before_student_%s_event_%s_or_vice_versa_or_together'
                                             % (s, event.id, s2, event2.id))

                            # If s1 and s2 are together, S_s1 = S_s2
                            self.m.addConstr(self.starts[s, event.id] >= self.starts[s2, event2.id]
                                             - 1001 * (1 - self.together[s, s2, event.id, event2.id]),
                                             'student_%s_event_%s_starts_with_student_%s_event_%s_if_together'
                                             % (s, event.id, s2, event2.id))

                            # If s1 and s2 are together, S_s1 = S_s2
                            self.m.addConstr(self.together[s2, s, event2.id, event.id] ==
                                             self.together[s, s2, event.id, event2.id],
                                             'student_%s_event_%s_together_symmetry_with_student_%s_event_%s'
                                             % (s, event.id, s2, event2.id))

                            for p, plane in self.planes.iteritems():
                                sortie = Sortie(None,plane)
                                sortie.studentSorties.append(ss)
                                sortie.studentSorties.append(ss2)
                                if sortie.feasible():
                                    # If s1 is before s2 on plane p, C_s1 <= S_s2
                                    self.m.addConstr(self.completes[s, event.id] <= self.starts[s2, event2.id]
                                                     + 1001 * (3 - self.pevents[p, s, event.id]
                                                               - self.pevents[p, s2, event2.id]
                                                               - self.before[s, event.id, s2, event2.id]
                                                               + self.together[s, s2, event.id, event2.id]),
                                                     'If_student_%s_event_%s_before_student_%s_event_%s_on_plane_%s_and_not_together_'
                                                     'they_cannot_overlap' % (s, event.id, s2, event2.id, p))

                            for i, instructor in self.instructors.iteritems():
                                sortie = Sortie(instructor)
                                sortie.studentSorties.append(ss)
                                sortie.studentSorties.append(ss2)
                                if sortie.feasible():
                                    # If s1 is before s2 with instructor i, C_s1 <= S_s2
                                    self.m.addConstr(self.completes[s, event.id] + event.debriefHours
                                                     <= self.starts[s2, event2.id]
                                                     + 1001 * (3 - self.ievents[i, s, event.id]
                                                               - self.ievents[i, s2, event2.id]
                                                               - self.before[s, event.id, s2, event2.id]
                                                               + self.together[s, s2, event.id, event2.id])
                                                     - event2.briefHours,
                                                     'If_student_%s_event_%s_before_student_%s_event_%s_with_instructor_%s_and_not_together_'
                                                     'they_cannot_overlap' % (s, event.id, s2, event2.id, i))
                for i, instructor in self.instructors.iteritems():
                    sortie = Sortie(instructor)
                    sortie.studentSorties.append(ss)
                    if sortie.feasible():
                        for dd in self.schedules:
                            self.m.addConstr(self.completes[s, event.id] <= self.starts[i, 'cr_%s' % (dd)]
                                         + 1001 * (2 - self.ievents[i, s, e]
                                                   - self.before[s, e, i, 'cr_%s' % (dd)]),
                                         'Student_%s_event_%s_finish_before_instructor_%s_crewrest_%s_if_before'
                                             % (s, event.id, i, dd))
                            self.m.addConstr(self.completes[i, 'cr_%s' % (dd)] <= self.starts[s, e]
                                         + 1001 * (2 - self.ievents[i, s, e]
                                                   - self.before[i, 'cr_%s' % (dd), s, e]),
                                         'Student_%s_event_%s_start_after_instructor_%s_crewrest_%s_if_after'
                                             % (s, e, i, dd))
                            self.m.addConstr(self.before[s, e, i, 'cr_%s' % (dd)]
                                             + self.before[i, 'cr_%s' % (dd), s, e] == 1,
                                             'Student_%s_event_%s_either_before_or_after_instructor_%s_crewrest_%s'
                                             % (s, e, i, dd))

                # Do not exceed max events per sortie
                self.m.addConstr(1 + quicksum(self.together[s, s2, e, event2.id]
                                              for s2, stud2 in self.students.iteritems() if s2 != s
                                              for event2 in stud2.findPossible(d, False)) <= event.maxStudents,
                                 'Do_not_exceed_max_students_for_event_%s_student_%s' % (e, s))
                # Do not exceed max weight on the plane
                pass
                # Student event sequence
                for event2 in event.followingEvents:
                    if (s, event2.id) in self.starts:
                        self.m.addConstr(self.completes[s, e] + event.debriefHours
                                         <= self.starts[s, event2.id] - event2.briefHours - (1 - event2.followsImmediately) * stud.crewDayHours,
                                         'Event_%s_must_precede_event_%s_for_student_%s' % (e, event2.id, s))
                # Student crew rest start
                for dd in self.schedules:
                    self.m.addConstr(self.completes[s, e] + event.debriefHours
                                     <= self.starts[s, 'cr_%s' % dd] + 1001 * (1 - self.before[s, event.id, s, 'cr_%s' % dd]),
                                     'Student_%s_event_%s_before_student_crewrest_%s' % (s, e, dd))
            for dd in self.schedules:
                # Crew rest must last at least 12 hours
                self.m.addConstr(self.starts[s, 'cr_%s' % dd] + stud.crewRestHours <= self.completes[s, 'cr_%s' % dd],
                                 'student_%s_crewrest_%s_at_least_%s_hours' % (s, dd, stud.crewRestHours))

                # Crew day must be less than 12 hours
                if (dd - 1) in self.schedules:
                    self.m.addConstr(self.completes[s, 'cr_%s' % (dd-1)] + stud.crewDayHours >= self.starts[s, 'cr_%s' % (dd)],
                                 'student_%s_crewday_%s_at_most_%s_hours' % (s, dd, stud.crewRestHours))

        # Do not exceed hours remaining on aircraft
        for p, plane in self.planes.iteritems():
            self.m.addConstr(quicksum(event.flightHours * self.pevents[p, s, event.id]
                                      for s, stud in self.students.iteritems()
                                      for event in stud.findPossible(d, False)
                                      if (p, s, event.id) in self.pevents)
                             <= plane.hours,
                             'Do_not_exceed_%s_hours_on_plane_%s' % (plane.hours, p))

        # Instructor crew rest
        for i, inst in self.instructors.iteritems():
            for dd in self.schedules:
                self.m.addConstr(self.starts[i, 'cr_%s' % (dd)] + inst.crewRestHours <= self.completes[i, 'cr_%s' % (dd)],
                                 'instructor_%s_crewrest_%s_at_least_%s_hours' % (i, dd, inst.crewRestHours))

                # Crew day must be less than 12 hours
                if (dd - 1) in self.schedules:
                    self.m.addConstr(self.completes[i, 'cr_%s' % (dd-1)] + stud.crewDayHours >= self.starts[i, 'cr_%s' % (dd)],
                                 'instructor_%s_crewday_%s_at_most_%s_hours' % (i, dd, inst.crewRestHours))


        # Student event release times - daylight enforcement

        # Student snivs

        # Instructor snivs

        # Max instructor events
        self.m.update()
        self.m.write("model.lp")
        """
        print "Constraints"
        for c in self.m.getConstrs():
            print('%s' % c.constrName)
        """

    #This function should take the output of an optimized model and write it as sorties and student sorties into the correct flight schedule
    def outputModel(self):
        for key, var in self.starts.iteritems():
            s = key[0]
            e = key[1]
            sor = Sortie()
            for i, inst in self.instructors.iteritems():
                if (i,s,e) in self.ievents and self.ievents[i,s,e].x:
                    sor.instructor = inst
                    break
            for p, plane in self.planes.iteritems():
                if (p,s,e) in self.pevents and self.pevents[p,s,e].x:
                    sor.plane = plane
                    break
            sor.takeoff = var.x
            sor.land = self.completes[key].x
            ss = StudentSortie()
            if s in self.students:
                ss.student = self.students[s]
            if e in self.syllabus:
                ss.event = self.syllabus[e]
                sor.studentSorties.append(ss)
                print str(sor)
            # else:
            #     print e, sor.takeoff, sor.land, s
        total = 0
        for key, val in self.pevents.iteritems():
            if val.x:
                total += 1
        print 'Total:', total
        """for key, val in self.together.iteritems():
            if val.x:
                print 'Together: ', key
        for key, val in self.before.iteritems():
            if val.x:
                print 'Before: ', key
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
                                        """
        return total


def main():
    pass

if __name__ == '__main__':
    main()

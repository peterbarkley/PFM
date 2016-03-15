from Squadron import Squadron
import Sortie
import StudentSortie
from Sniv import Sniv
from Flyer import Flyer
from Instructor import Instructor
from Odd import Student
from gurobipy import *
from datetime import timedelta

class TrainingSquadron(Squadron):

    def __init__(self, *initial_data, **kwargs):
        self.devices = {}
        self.organization_ID = None
        self.forecasts = []
        self.events = {}
        self.constraints = {}
        self.tags = {}
        self.x = tuplelist()
        self.y = tuplelist()
        self.slots = tuplelist()
        self.verboser = False
        self.student_turnaround = timedelta(hours=1)
        super(TrainingSquadron, self).__init__(*initial_data, **kwargs)

    # Returns the min priority value across forecasts that overlap with w
    def wavePriority(self, w):
        return 1

    def createVariables(self):
        base_tier = 0
        objective = LinExpr()
        for day, schedule in self.schedules.items():
            if self.verboser:
                print day
            for wave in schedule.waves.values():

                tier = base_tier + min(wave.tier(), self.max_events - 1)
                if self.verboser:
                    print wave, tier
                for student in self.students.values():
                    if self.verboser:
                        print student
                    for e, syllabus in student.event_tier(tier):
                        event = self.events[e]
                        if self.verboser:
                            print day, event
                        for device in self.devices.values():
                            if self.verboser:
                                n = '%s_%s_%s_day_%s_%s' % (student, event, device, day, wave)
                                print n
                                print device, device.tags, student.tags, device.category, event.device_category, wave.tags
                            # Future work: filter for device availability
                            # Future work: filter for wave matching event constraints (night vs day)
                            if device.tags <= student.tags and device.category == event.device_category and device.category in wave.tags:
                                self.x += [(student, event, device, day, wave)]
                                n = '%s_%s_%s_day_%s_%s' % (student, event, device, day, wave)
                                self.sevents[student, event, device, day, wave] = self.m.addVar(vtype=GRB.BINARY,
                                                                                   name=n)
                                objective.add(schedule.priority *
                                              wave.priority *
                                              student.getPriority() *
                                              self.sevents[(student, event, device, day, wave)])
                for instructor in self.instructors.values():
                    # Future work: filter for instructor availability
                    if self.verboser:
                        print instructor
                    for device in self.devices.values():
                        if self.verboser:
                            print device, device.tags, instructor.tags
                        if device.tags <= instructor.tags and device.category in wave.tags:  # Future work: filter for device availability
                            n = '%s_%s_day_%s_%s' % (instructor, device, day, wave)
                            # print n
                            self.y += [(instructor, device, day, wave)]
                            self.ievents[instructor, device, day, wave] = self.m.addVar(vtype=GRB.BINARY,
                                                                               name=n)
                            prefCoefficient = 1.0  # inst.getPreference(d,w)
                            if self.militaryPreference and instructor.paid:
                                prefCoefficient = 0.1 * prefCoefficient
                            objective.add(device.getPriority(wave) *
                                          schedule.priority *
                                          instructor.getPreference(day, wave) *
                                          self.ievents[instructor, device, day, wave])

            base_tier += self.max_events
        self.m.update()
        self.m.setObjective(objective, GRB.MAXIMIZE)
        self.m.update()

    def constructModel(self):
        se = self.sevents
        ie = self.ievents
        x = self.x.select
        y = self.y.select
        # print self.y.select('*','*','*','*')

        # Hard scheduled events constraint

        # Formation flight constraint
        for student, event, device, day, wave in x('*', '*', '*', '*', '*'):
            #  Assign an eligible instructor for each student event
            self.m.addConstr(se[student, event, device, day, wave] <=
                             quicksum(ie[instructor, device, day, wave]
                                      for instructor, device, day, wave
                                      in y('*', device, day, wave)
                                      if self.eligible(event, instructor=instructor, student=student, )))

        for day, schedule in self.schedules.items():
            for wave in schedule.waves.values():
                # Aircraft launches per slot time period must not exceed assigned squadron airfield slots
                # Future work: replace the 3 with a database entry tied to aircraft airfield category and squadron
                # Future work: should be looping over all waves that start within specific hourly periods
                self.m.addConstr(quicksum(ie[instructor, device, day, wave]
                                          for instructor, device, day, wave
                                          in y('*', '*', day, wave)
                                          if device.category == 'aircraft') <= 3,
                                 'Do_not_exceed_3_aircraft_per_hour_on_day_%s_%s' % (day, wave))
                for device in self.devices.values():
                    if device.category in wave.tags:
                        if len(x('*', '*', device, day, wave)) > 0:
                            #  Require sufficient time for all the events to be completed
                            self.m.addConstr(quicksum(event.deviceHours() * se[student, event, device, day, wave]
                                                      for student, event, device, day, wave in
                                                      x('*', '*', device, day, wave)) <= wave.planeHours(),
                                             'All_events_must_fit_within_wave_device_hours_on_day_%s_%s_for_%s'
                                             % (day, wave, device))
                        # Do not exceed device slot instructor capacity
                        self.m.addConstr(quicksum(ie[instructor, device, day, wave]
                                          for instructor, device, day, wave
                                          in y('*', device, day, wave)) <= device.instructor_capacity,
                                         '%s_can_only_hold_%s_instructors_on_day_%s_during_%s' %
                                         (device, device.instructor_capacity, day, wave))
                        # Do not exceed device slot student capacity
                        self.m.addConstr(quicksum(se[student, event, device, day, wave]
                                                      for student, event, device, day, wave in
                                                      x('*', '*', device, day, wave)) <= device.student_capacity,
                                         '%s_can_only_hold_%s_students_on_day_%s_during_%s' %
                                         (device, device.student_capacity, day, wave))
                # Instructor can only be in one device at a time
                # Future work: filter for instructor availability
                for instructor in self.instructors.values():
                    self.m.addConstr(quicksum(ie[instructor, device, day, wave]
                                              for instructor, device, day, wave
                                              in y(instructor, '*', day, wave)) <= 1,
                                     '%s_cannot_be_in_more_than_one_device_on_day_%s_during_%s' %
                                     (instructor, day, wave))

            # Do not schedule plane in overlapping wave pairs
            for (i, j) in schedule.exclusiveWaves["Plane"]:
                for device in self.devices.values():
                    # Future work: exclusiveWaves should return actual waves
                    wave_i = schedule.waves[i]
                    wave_j = schedule.waves[j]
                    if device.category in wave_i.tags and device.category in wave_j.tags:
                        self.m.addConstr(quicksum(ie[instructor, device, day, wave_i] for instructor, device, day, wave_i in self.y.select('*', device, day, wave_i)) +
                                         quicksum(ie[instructor, device, day, wave_j] for instructor, device, day, wave_j in self.y.select('*', device, day, wave_j)) <= 1,
                                         'Do_not_schedule_%s_on_day_%s_for_%s_and_%s_because_they_overlap' %
                                         (device, day, wave_i, wave_j))

            for (i, j) in schedule.exclusiveWaves["Flyer"]:
                # Future work: exclusiveWaves should return actual waves
                wave_i = schedule.waves[i]
                wave_j = schedule.waves[j]
                # Do not schedule instructor in overlapping wave pairs
                for instructor in self.instructors.values():

                    self.m.addConstr(quicksum(ie[instructor, device, day, wave_i]
                                              for instructor, device, day, wave_i
                                              in y(instructor, '*', day, wave_i)) +
                                     quicksum(ie[instructor, device, day, wave_j]
                                              for instructor, device, day, wave_j
                                              in y(instructor, '*', day, wave_j)) <= 1,
                                     'Do_not_schedule_%s_on_day_%s_for_%s_and_%s_because_they_overlap' %
                                     (instructor, day, wave_i, wave_j))

                # Do not schedule student in overlapping wave pairs
                for student in self.students.values():
                    self.m.addConstr(quicksum(se[student, event, device, day, wave_i]
                                              for student, event, device, day, wave_i
                                              in x(student, '*', '*', day, wave_i)) +
                                     quicksum(se[student, event, device, day, wave_j]
                                              for student, event, device, day, wave_j
                                              in x(student, '*', '*', day, wave_j)) <= 1,
                                     'Do_not_schedule_%s_on_day_%s_for_%s_and_%s_because_they_overlap' %
                                     (student, day, wave_i, wave_j))

            # Do not exceed student crew day
            # Do not exceed instructor crew day
            if day + 1 in self.schedules:
                # Do not exceed student crew rest
                # Future work: either loop over individual events or add continuous crewrest[student, day] vars
                for (late_wave, early_wave) in self.crewrest_pairs(day, 'Student'):
                    for student in self.students.values():
                        self.m.addConstr(quicksum(se[student, event, device, day, late_wave]
                                                  for student, event, device, day, late_wave
                                                  in x(student, '*', '*', day, late_wave)) +
                                         quicksum(se[student, event, device, day_two, early_wave]
                                                  for student, event, device, day_two, early_wave
                                                  in x(student, '*', '*', day + 1, early_wave)) <= 1,
                                         'Do_not_schedule_%s_for_%s_on_day_%s_and_%s_the_next_day_because_of_crewrest' %
                                         (student, day, late_wave, early_wave))

                # Do not exceed instructor crew rest
                for (late_wave, early_wave) in self.crewrest_pairs(day, 'Instructor'):
                    for instructor in self.instructors.values():
                        self.m.addConstr(quicksum(ie[instructor, device, day, late_wave]
                                                  for instructor, device, day, late_wave
                                                  in y(instructor, '*', day, late_wave)) +
                                         quicksum(ie[instructor, device, day_two, early_wave]
                                                  for instructor, device, day_two, early_wave
                                                  in y(instructor, '*', day + 1, early_wave)) <= 1,
                                         'Do_not_schedule_%s_for_%s_on_day_%s_and_%s_the_next_day_because_of_crewrest' %
                                         (instructor, day, late_wave, early_wave))

            # Do not exceed max graded events for a student
            for student in self.students.values():
                self.m.addConstr(quicksum(se[student, event, device, day, wave]
                                          for student, event, device, day, wave
                                          in x(student, '*', '*', day, '*')
                                          if event.graded) <= self.max_events,
                                 'No_more_than_%d_graded_events_for_%s_on_day_%s' % (self.max_events, student, day))

            for device in self.devices.values():
                if device.category == 'room':
                    for student, event, device, day, wave in x('*', '*', device, day, '*'):
                        for student2, event2, device, day, wave in x('*', '*', device, day, wave):
                            if event != event2 and student != student2:
                                self.m.addConstr(se[student, event, device, day, wave] +
                                                 se[student2, event2, device, day, wave] <= 1,
                                                 'If_%s_%s_scheduled_in_%s_on_day_%s_%s_do_not_scheduled_%s_%s'
                                                 % (student, event, device, day, wave, student2, event2))

        # Schedule each event no more than once
        for student in self.students.values():
            for e, syllabus in student.event_tier(self.max_events * self.days):
                event = self.events[e]
                self.m.addConstr(quicksum(se[student, event, device, day, wave]
                                          for student, event, device, day, wave in
                                          x(student, event, '*', '*', '*')) <= 1,
                                 'Schedule_%s_%s_not_more_than_once' % (student, event))
                # Schedule all new ancestors(e) in a wave ending before w (or to w) if assigning e to w
                parents = syllabus.parents(e)
                if not parents <= student.progressing:
                    for day, schedule in self.schedules:
                        for wave in schedule.waves.values():
                            if len(x(student, event, '*', day, wave)) > 0:
                                self.m.addConstr(len(parents - student.progressing) *
                                                 quicksum(se[student, event, device, day, wave]
                                                          for student, event, device, day, wave in
                                                          x(student, event, '*', day, wave)) <=
                                                 quicksum(se[student, event2, device, day2, wave2]
                                                          for student, event2, device, day2, wave2 in
                                                          x(student, '*', '*', '*', '*')
                                                          if event2.event_ID in parents and
                                                          (wave2.times["Student"].end + self.student_turnaround <=
                                                           wave.times["Student"].begin or
                                                           wave2 == wave)),
                                                 'Schedule_parent_events_before_scheduling_%s_%s_on_day_%s_%s'
                                                 % (student, event, day, wave))

        self.m.update()
        self.m.write('model.lp')

    def crewrest_pairs(self, day, resource_type):
        pairs = []
        if resource_type == "Student":
            s = Student(id="Sample", squadron=self)
        elif resource_type == "Instructor":
            s = Instructor(id="Sample")
        else:
            s = Flyer(id="Sample")
        for wave1 in self.schedules[day].waves.values():
            rest = Sniv()
            rest.begin = wave1.times[resource_type].end
            rest.end = rest.begin + s.crewRest()
            s.snivs[0]=rest
            if day + 1 in self.schedules:
                for wave2 in self.schedules[day + 1].waves.values():
                    if not s.available(self.schedules[day + 1].day, wave2):
                        pairs.append((wave1, wave2))
        return pairs

    def eligible(self, event, **resources):
        for constraint in event.constraints:
            #  Future work: implement other verbs beside 'is'
            #  Merge entries to form constraint target tag
            target_tag = self.tags[constraint.object_tag_ID]
            if constraint.object_resource_ID is not None:
                target_tag += '_for_' + str(constraint.object_resource_ID)
            elif constraint.object_resource_type is not None and constraint.object_resource_type in resources:
                target_tag += '_for_' + str(resources[constraint.object_resource_type].id)
            if self.verbose:
                print target_tag
            #  Not valid if subject resource type does not have the required tag
            if (constraint.subject_resource_type in resources) == constraint.positive:
                print resources[constraint.subject_resource_type].tags
                if target_tag not in resources[constraint.subject_resource_type].tags:
                    return False

        return True

    def no_overlapping_devices(self, day, schedule, wave):
        pass

    def outputModel(self):
        for (instructor, device, day, wave) in self.y:
            if self.ievents[instructor, device, day, wave].x:
                sortie = Sortie.Sortie()
                sortie.instructor = instructor #Instructor object
                sortie.plane = device #Plane object
                sortie.wave = wave #Wave ojbect
                sortie.brief = wave.times["Flyer"].begin
                sortie.takeoff = wave.times["Plane"].begin
                sortie.land = wave.times["Plane"].end
                self.schedules[day].sorties[(device, wave)] = sortie
        for (student, event, device, day, wave) in self.x:
            if self.sevents[student, event, device, day, wave].x:
                ss = StudentSortie.StudentSortie()
                ss.student = student
                ss.event = event
                self.schedules[day].sorties[(device, wave)].studentSorties.append(ss)
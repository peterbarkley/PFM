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
        self.airfield = None
        self._crewday_pairs = {}
        super(TrainingSquadron, self).__init__(*initial_data, **kwargs)

    # Returns the min priority value across forecasts that overlap with w
    def wavePriority(self, wave, event):
        priority = 1.0
        if "room" in wave.tags:
            priority = 0.5
        elif event.device_category == 'aircraft':
            for forecast in self.forecasts:
                if (forecast['begin'] <= wave.times["Plane"].end and
                        forecast['end'] >= wave.times["Plane"].begin and
                        forecast['tag'] == event.stage):
                    priority = min(priority, forecast['probability'])
        return priority

    def createVariables(self):
        if self.verbose:
            print "Creating variables"
        base_tier = 0
        objective = LinExpr()

        # Loop over days, waves, students, events, and devices creating decision variables
        # Check to make sure events could feasibly be scheduled in that day and wave
        # Check to make sure event could be feasibly scheduled on that device
        # Check to make sure student is qualified on that device
        # If student event is hard scheduled, only build variables for acceptable devices and waves
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
                    if student.available(schedule.day, wave):
                        for event, syllabus in student.event_tier(tier):
                            # event = self.events[e]
                            if self.verboser:
                                print day, event
                            acceptable = True
                            if ((student, event) in schedule.hardschedule and
                                    (schedule.hardschedule[(student, event)]['wave'] is not None) and
                                    wave != schedule.hardschedule[(student, event)]['wave']):
                                acceptable = False

                            if (acceptable and (event.device_category in wave.tags) and
                                    wave.night_time >= event.min_night_hours and
                                    wave.day_time >= event.min_day_hours):
                                if ((student, event) in schedule.hardschedule and
                                        (schedule.hardschedule[(student, event)]['device'] is not None)):
                                    devices = [schedule.hardschedule[(student, event)]['device']]
                                else:
                                    devices = self.devices.values()
                                for device in devices:
                                    if self.verboser:
                                        n = '%s_%s_%s_day_%s_%s' % (student, event, device, day, wave)
                                        print n
                                        print device, device.tags, student.tags, \
                                            device.category, event.device_category, wave.tags
                                    # Future work: filter for device availability
                                    # Future work: filter for wave matching event constraints (night vs day)
                                    if (device.tags <= student.tags and
                                            device.category == event.device_category and
                                            device.category in wave.tags):
                                        self.x += [(student, event, device, day, wave)]
                                        n = '%s_%s_%s_day_%s_%s' % (student, event, device, day, wave)
                                        self.sevents[student, event, device, day, wave] = self.m.addVar(vtype=GRB.BINARY,
                                                                                                        name=n)
                                        objective.add(schedule.priority *
                                                      self.wavePriority(wave, event) *
                                                      student.getPriority() *
                                                      self.sevents[(student, event, device, day, wave)])

                # Loop over days, waves, instructors and devices creating instructor decision variables
                for instructor in self.instructors.values():
                    # Future work: filter for instructor availability
                    if self.verboser:
                        print instructor
                    if instructor.available(schedule.day, wave):
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
                                objective.add(device.getPriority(wave) *
                                              schedule.priority *
                                              instructor.getPreference(day, wave) *
                                              self.ievents[instructor, device, day, wave])

            base_tier += self.max_events
        self.m.update()
        self.m.setObjective(objective, GRB.MAXIMIZE)
        self.m.update()

    def constructModel(self):
        if self.verbose:
            print "Adding constraints"
        se = self.sevents
        ie = self.ievents
        x = self.x.select
        y = self.y.select
        # print self.y.select('*','*','*','*')


        # Formation flight constraint

        for student, event, device, day, wave in se:
            #  Assign an eligible instructor for each student event
            if ((student, event) not in self.schedules[day].hardschedule) or \
                    (self.schedules[day].hardschedule[(student, event)]['instructor'] is None):
                self.m.addConstr(se[student, event, device, day, wave] <=
                                 quicksum(ie[instructor, device, day, wave]
                                          for instructor, device, day, wave
                                          in y('*', device, day, wave)
                                          if self.eligible(event, instructor=instructor, student=student, )),
                                 'Schedule_eligible_instructor_for_%s_%s_%s_day_%s_%s' %
                                 (student, event, device, day, wave))
            # Hard scheduled instructor constraint
            else:
                instructor = self.schedules[day].hardschedule[(student, event)]['instructor']
                self.m.addConstr(se[student, event, device, day, wave] <=
                                 quicksum(ie[instructor, device, day, wave]
                                          for instructor, device, day, wave
                                          in y(instructor, device, day, wave)),
                                 '%s_hard_scheduled_for_%s_%s_%s_day_%s_%s' %
                                 (instructor, student, event, device, day, wave))

        for day, schedule in self.schedules.items():
            # Hard scheduled event constraint
            for student, event in schedule.hardschedule:
                self.m.addConstr(quicksum(se[student, event, device, day, wave]
                                          for student, event, device, day, wave in
                                          x(student, event, '*', day, '*')) == 1,
                                 'Hard_schedule_%s_%s_on_day_%s' % (student, event, day))
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
                            students_per_instructor = 1
                            if device.category == 'room':  # Really should come from the event media
                                students_per_instructor = device.student_capacity
                            self.m.addConstr(quicksum(event.deviceHours() * se[student, event, device, day, wave]
                                                      for student, event, device, day, wave in
                                                      x('*', '*', device, day, wave)) <=
                                             wave.planeHours() * students_per_instructor,
                                             'All_events_must_fit_within_wave_device_hours_on_day_%s_%s_for_%s'
                                             % (day, wave, device))
                            if device.category == 'aircraft':  # Really should come from the event media
                                #  Require sufficient night time for all the events to be completed
                                self.m.addConstr(quicksum(event.min_night_hours * se[student, event, device, day, wave]
                                                          for student, event, device, day, wave in
                                                          x('*', '*', device, day, wave)) <=
                                                 wave.night_time,
                                                 'Event_min_night_hours_less_than_wave_night_hours_on_day_%s_%s_for_%s'
                                                 % (day, wave, device))
                                #  Require sufficient day time for all the events to be completed
                                self.m.addConstr(quicksum(event.min_day_hours * se[student, event, device, day, wave]
                                                          for student, event, device, day, wave in
                                                          x('*', '*', device, day, wave)) <=
                                                 wave.day_time,
                                                 'Event_min_day_hours_less_than_wave_night_hours_on_day_%s_%s_for_%s'
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
                # Do not exceed student crew day
                for (early_wave, late_wave) in self.crewday_pairs(day, 'Student'):
                    for student in self.students.values():
                        self.m.addConstr(quicksum(se[student, event, device, day, late_wave]
                                                  for student, event, device, day, late_wave
                                                  in x(student, '*', '*', day, late_wave)) +
                                         quicksum(se[student, event, device, day_two, early_wave]
                                                  for student, event, device, day_two, early_wave
                                                  in x(student, '*', '*', day, early_wave)) <= 1,
                                         'Do_not_schedule_%s_for_%s_and_%s_on_day_%s_because_of_crewday' %
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
                # Do not exceed instructor crew day
                for (early_wave, late_wave) in self.crewday_pairs(day, 'Instructor'):
                    for instructor in self.instructors.values():
                        self.m.addConstr(quicksum(ie[instructor, device, day, late_wave]
                                                  for instructor, device, day, late_wave
                                                  in y(instructor, '*', day, late_wave)) +
                                         quicksum(ie[instructor, device, day_two, early_wave]
                                                  for instructor, device, day_two, early_wave
                                                  in y(instructor, '*', day, early_wave)) <= 1,
                                         'Do_not_schedule_%s_for_%s_and_%s_on_day_%s_because_of_crewday' %
                                         (instructor, day, late_wave, early_wave))

            # Do not exceed max graded events for a student
            for student in self.students.values():
                self.m.addConstr(quicksum(se[student, event, device, day, wave]
                                          for student, event, device, day, wave
                                          in x(student, '*', '*', day, '*')
                                          if event.graded) <= self.max_events,
                                 'No_more_than_%d_graded_events_for_%s_on_day_%s' % (self.max_events, student, day))
            # Only one lesson in a class per wave
            for device in self.devices.values():
                if device.category == 'room':
                    for student, event, device, day, wave in x('*', '*', device, day, '*'):
                        for student2, event2, device, day, wave in x('*', '*', device, day, wave):
                            if event != event2 and student != student2:
                                self.m.addConstr(se[student, event, device, day, wave] +
                                                 se[student2, event2, device, day, wave] <= 1,
                                                 'If_%s_%s_scheduled_in_%s_on_day_%s_%s_do_not_schedule_%s_%s'
                                                 % (student, event, device, day, wave, student2, event2))

        for student in self.students.values():
            # Schedule partners together
            p = student.partner_student_ID
            if p in self.students:
                partner = self.students[p]
                if student.event_tier(0) == partner.event_tier(0):
                    for student, event, device, day, wave in x(student, '*', '*', '*', '*'):
                        self.m.addConstr(se[student, event, device, day, wave] ==
                                         quicksum(se[partner, event, device, day, wave]
                                                  for partner, event, device, day, wave in
                                                  x(partner, event, device, day, wave)),
                                         'Schedule_partners_%s_and_%s_together_for_%s_in_%s_on_day_%s_%s'
                                         % (student, partner, event, device, day, wave))
            # Schedule each event no more than once
            for event, syllabus in student.event_tier(self.max_events * self.days):
                # event = self.events[e]
                self.m.addConstr(quicksum(se[student, event, device, day, wave]
                                          for student, event, device, day, wave in
                                          x(student, event, '*', '*', '*')) <= 1,
                                 'Schedule_%s_%s_not_more_than_once' % (student, event))
                # Schedule all new ancestors(e) in a wave ending before w (or to w) if assigning e to w
                parents = syllabus.parents(event)
                if not parents <= student.progressing:
                    for day, schedule in self.schedules.items():
                        for wave in schedule.waves.values():
                            if len(x(student, event, '*', day, wave)) > 0:
                                for student, event2, device, day2, wave2 in x(student, '*', '*', '*', '*'):
                                    pass 
                                    """if event2, syllabus in parents and
                                    (wave2.times["Student"].end + self.student_turnaround <=
                                    wave.times["Student"].begin or
                                    wave2 == wave"""
                                self.m.addConstr(len(parents - student.progressing) *
                                                 quicksum(se[student, event, device, day, wave]
                                                          for student, event, device, day, wave in
                                                          x(student, event, '*', day, wave)) <=
                                                 quicksum(se[student, event2, device, day2, wave2]
                                                          for student, event2, device, day2, wave2 in
                                                          x(student, '*', '*', '*', '*')
                                                          if (event2, syllabus) in parents and
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
            s.snivs[0] = rest
            if day + 1 in self.schedules:
                for wave2 in self.schedules[day + 1].waves.values():
                    if not s.available(self.schedules[day + 1].day, wave2):
                        pairs.append((wave1, wave2))
        return pairs

    # Returns tuples of wave objects (early, late) that cannot both be scheduled within crewday
    def crewday_pairs(self, day, resource_type):
        crewday = 12
        if (day, resource_type) in self._crewday_pairs:
            return self._crewday_pairs[day, resource_type]

        pairs = []

        for wave1 in self.schedules[day].waves.values():
                for wave2 in self.schedules[day].waves.values():
                    if wave2.times[resource_type].end - wave1.times[resource_type].begin > timedelta(hours=crewday):
                        pairs.append((wave1, wave2))
        self._crewday_pairs[day, resource_type] = pairs
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
            if self.verboser:
                print event, target_tag, constraint.__dict__, resources
            #  Not valid if subject resource type does not have the required tag
            if (constraint.subject_resource_type in resources) == constraint.positive:
                if self.verboser:
                    print resources[constraint.subject_resource_type], resources[constraint.subject_resource_type].tags
                if target_tag not in resources[constraint.subject_resource_type].tags:
                    return False

        return True

    def no_overlapping_devices(self, day, schedule, wave):
        pass

    def outputModel(self):
        for (instructor, device, day, wave) in self.y:
            if self.ievents[instructor, device, day, wave].x:
                sortie = Sortie.Sortie()
                sortie.instructor = instructor  # Instructor object
                sortie.plane = device  # Plane object
                sortie.wave = wave  # Wave object
                sortie.brief = wave.times["Flyer"].begin
                sortie.takeoff = wave.times["Plane"].begin
                sortie.land = wave.times["Plane"].end
                self.schedules[day].sorties[(device, wave)] = sortie
        for (student, event, device, day, wave) in self.x:
            if self.sevents[student, event, device, day, wave].x:
                schedule = self.schedules[day]
                sortie = schedule.sorties[(device, wave)]
                if (student, event) in schedule.hardschedule:
                    ss = StudentSortie.StudentSortie(schedule.hardschedule[(student, event)])
                    sortie.sortie_ID = schedule.hardschedule[(student, event)]['sortie_ID']
                else:
                    ss = StudentSortie.StudentSortie()
                    ss.student = student
                    ss.event = event
                sortie.studentSorties.append(ss)
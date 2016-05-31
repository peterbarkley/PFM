from datetime import datetime, timedelta
from gurobipy import *
from graph import graph

class VUP(object):

    def __init__(self, *initial_data, **kwargs):
        self.personnel = set()
        self.jobs = set()
        self.days = 1
        self.tags = []
        self.unique_tags = []
        self.x = tuplelist()
        self.e = tuplelist()
        self.s = tuplelist()
        self.job_vars = {}
        self.obj_vars = {}
        self.m = Model()
        self.timeLimit = 60
        self.job_shifts = tuplelist()
        self.job_data = {}
        self.groups = [{'JAX'}]  # {'MPO'}, {'JO'}, {'DH'}]  # {'TC'}, {'CP', 'GUAM'}, {'CP', 'JAX'}]
        self.start = datetime.today()
        self.schedule = []
        self.cliques = {}
        self.summary = {}
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    # Finds waves that exclude each other
    def findcliques(self, h, flight):
        # i = 0
        cliques = {}
        for p in self.personnel:
            if tuple(p.tags) not in self.cliques:

                g = graph()
                for (duty, start, stop) in self.job_shifts:
                    d = self.job_data[(duty, start, stop)]
                    if d['tags'] <= p.tags and ((not flight) or d['flight'] > 0):
                        n1 = (duty, start, stop)
                        g.add_node(n1)
                        for (duty2, start2, stop2) in self.job_shifts:
                            d2 = self.job_data[(duty2, start2, stop2)]
                            if d2['tags'] <= p.tags and ((not flight) or d2['flight'] > 0):
                                n2 = (duty2, start2, stop2)
                                if n1 != n2 and stop2 + h > start and start2 < stop + h:
                                    g.add_node(n2)
                                    g.add_edge(n1, n2)
                cliques[tuple(p.tags)] = g.find_all_cliques()
                # print tuple(p.tags), self.cliques[tuple(p.tags)]
        return cliques

    def buildSorties(self):
        for job in self.jobs:
            for i in range(0, job.number):
                for (duty, number, flight_multiple), tags in job.duties.iteritems():
                    if tags not in self.unique_tags:
                        self.unique_tags.append(tags)
                        j = len(self.unique_tags) - 1
                    else:
                        j = self.unique_tags.index(tags)
                    shift_cum = 0
                    for (non_flight, flight) in job.shifts:
                        start = job.start + shift_cum + i * job.between
                        stop = start + non_flight + flight
                        job_shift = (duty, start, stop)
                        self.job_shifts += [job_shift]
                        self.job_data[job_shift] = {'number': number, 'tags': tags, 'flight': flight_multiple*flight}

                        shift_cum += non_flight + flight + job.btshifts

    def writeSchedule(self):

        self.createVariables()

        self.constructModel()
        model = self.m

        model.params.timeLimit = self.timeLimit
        model.update()

        model.write('model.lp')
        model.optimize()

        if model.status == GRB.status.INF_OR_UNBD:
            # Turn presolve off to determine whether model is infeasible
            # or unbounded
            model.setParam(GRB.param.presolve, 0)
            model.optimize()

        if model.status == GRB.status.OPTIMAL or model.status == GRB.status.TIME_LIMIT:
            print('Optimal objective: %g' % model.objVal)
            model.write('model.sol')
            self.outputModel()
            return False
        elif model.status != GRB.status.INFEASIBLE:
            print('Optimization was stopped with status %d' % model.status)
            model.write('model.sol')
            return True
        else:
            # Model is infeasible - compute an Irreducible Inconsistent Subsystem (IIS)
            print('')
            print('Model is infeasible')
            model.computeIIS()
            model.write("model.ilp")
            print("IIS written to file 'model.ilp'")
            return True

    def createVariables(self):
        for (duty, start, stop) in self.job_shifts:
            for p in self.personnel:
                if self.job_data[(duty, start, stop)]['tags'] <= p.tags:
                    n = p.id + '_' + duty + '_' + str(start)
                    self.x += [(p, duty, start, stop)]
                    self.job_vars[p, duty, start, stop] = self.m.addVar(vtype=GRB.BINARY, name=n)

        objective = LinExpr()
        i = 0
        for c in self.groups:
            n = '_'.join(c)
            self.obj_vars[i] = self.m.addVar(vtype=GRB.CONTINUOUS, name=n+'_minimax')
            objective.add(self.obj_vars[i])
            i += 1

        self.m.update()
        self.m.setObjective(objective, GRB.MINIMIZE)
        self.m.update()

    def constructModel(self):
        # Assign n people to each job
        for (duty, start, stop) in self.job_shifts:
            n = self.job_data[(duty, start, stop)]['number']
            self.m.addConstr(quicksum(self.job_vars[p, duty, start, stop]
                                      for (p, duty, start, stop)
                                      in self.x.select('*', duty, start, stop)) == n,
                             name=duty+str(start)+'_'+str(stop))

        # Weekly flight hours must be less than 50
        print "Starting weekly"
        period = 7
        # cliques = self.findcliques(24*period, True)
        for p in self.personnel:
            for d in range(0, self.days):
                self.m.addConstr(quicksum(self.job_data[(duty, start, stop)]['flight'] *
                                          self.job_vars[p, duty, start, stop]
                                          for (p, duty, start, stop) in self.x.select(p, '*', '*', '*')
                                          if 24*d <= start <= 24*(d+7)) <= 50,
                                 name='Do_not_exceed_max_flight_in_%s_days_person_%s_%s' % (period, p.id, d))

        # Do not assign people to overlapping jobs
        """for p in self.personnel:
            for (p, duty, start, stop) in self.x.select(p, '*', '*', '*'):
                for (p, duty2, start2, stop2) in self.x.select(p, '*', '*', '*'):
                    if (duty, start, stop) != (duty2, start2, stop2) and stop2 + 12 > start and start2 < stop + 12:
                        self.m.addConstr(self.job_vars[p, duty, start, stop] +
                                         self.job_vars[p, duty2, start2, stop2] <= 1,
                                         name='job_%s_with_start_%s_and_stop_%s_overlaps_with_job_%s_start_%s_stop_%s'
                                              '_for_person_%s' % (duty, start, stop, duty2, start2, stop2, p.id))
        """
        # Second attempt at overlapping jobs using cliques
        cliques = self.findcliques(12, False)
        for p in self.personnel:
            i = 0
            for clique in cliques[tuple(p.tags)]:
                self.m.addConstr(quicksum(self.job_vars[p, duty, start, stop] for (duty, start, stop) in clique) <= 1,
                                 name='Do_not_double_schedule_person_'+p.id+'_'+str(i))
                i += 1

        # Ensure obj_var is max of sum of duties across class
        i = 0
        for c in self.groups:
            n = '_'.join(c)
            for p in self.personnel:
                if c <= p.tags:
                    self.m.addConstr(quicksum((stop - start) * self.job_vars[p, duty, start, stop] for
                                              (p, duty, start, stop) in self.x.select(p, '*', '*', '*'))
                                     <= self.obj_vars[i], name='minimax_'+p.id+'_'+n)
            i += 1
        pass

    def outputModel(self):
        sorties = {}
        stats = {}
        for p in self.personnel:
            stats[p] = {'flight_hours': 0,
                        'duty_hours': 0,
                        'total_hours': 0,
                        'days_not_scheduled':0,
                        'free_days': 0,
                        'training_days': 0,
                        'count': 1}
            sorties[p] = []

        for (p, duty, start, stop) in self.x:
            if self.job_vars[p, duty, start, stop].x:
                a = self.start + timedelta(hours=start)
                b = self.start + timedelta(hours=stop)
                self.schedule.append({'person': p.id,
                                      'duty': duty,
                                      'start': a,
                                      'stop': b,
                                      'tags': p.tags})
                stats[p]['flight_hours'] += self.job_data[(duty, start, stop)]['flight']
                if duty[0:3] == 'Duty':
                    stats[p]['duty_hours'] += stop - start
                stats[p]['total_hours'] += stop - start
                sorties[p].append({'start': start,
                                   'stop': stop})
        self.schedule = sorted(self.schedule, key=lambda s: (s['start'], s['duty']))
        summary = {}
        reporting_groups = [{'JO', 'TC'}, {'JO', 'CP'}, {'MPO'}, {'DH'}]
        for group in reporting_groups:
            summary[tuple(group)] = {'days_not_scheduled':0,
                                     'free_days': 0,
                                     'training_days': 0,
                                     'flight_hours': 0,
                                     'duty_hours': 0,
                                     'total_hours': 0,
                                     'count': 0}

        for p in self.personnel:
            t = sorted(sorties[p], key=lambda s: s['start'])
            for i in range(0, len(t)-1):
                diff = t[i+1]['start'] - t[i]['stop']
                stats[p]['days_not_scheduled'] += diff/24
                stats[p]['free_days'] += (diff - 12)/24
            stats[p]['training_days'] = self.days - stats[p]['days_not_scheduled']
            for group in reporting_groups:
                if group <= p.tags:
                    for key in summary[tuple(group)]:
                        summary[tuple(group)][key] += stats[p][key]
        for group in reporting_groups:
            keys = summary[tuple(group)].keys()
            for key in keys:
                summary[tuple(group)]['ave_'+key] = float(summary[tuple(group)][key])/float(summary[tuple(group)]['count'])
            print group, summary[tuple(group)]
        self.summary = summary


def main():
    pass

if __name__ == '__main__':
    main()


from gurobipy import *


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
        self.groups = [{'MPO'}, {'TC'}, {'CP'}]
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def buildSorties(self):
        for job in self.jobs:
            for i in range(0, job.number):
                for (duty, number), tags in job.duties.iteritems():
                    if not tags in self.unique_tags:
                        self.unique_tags.append(tags)
                        j = len(self.unique_tags) - 1
                    else:
                        j = self.unique_tags.index(tags)
                    shift_cum = 0
                    for shift in job.shifts:
                        start = job.start + shift_cum + i * job.between
                        stop = start + shift
                        job_shift = (duty,
                                     start,
                                     stop,
                                     number,
                                     j)
                        self.job_shifts += [job_shift]  # (name, start, stop, number, tags_index)

                        shift_cum += shift

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
        i = 0

        for tags in self.unique_tags:
            for p in self.personnel:
                if tags <= p.tags:
                    for (duty, start, stop, number, i) in self.job_shifts.select('*', '*', '*', '*', i):

                        n = p.id + '_' + duty + str(start)
                        self.x += [(p, duty, start, stop, number)]
                        self.job_vars[p, duty, start, stop, number] = self.m.addVar(vtype=GRB.BINARY, name=n)
            i += 1

        objective = LinExpr()
        i = 0
        for c in self.groups:
            self.obj_vars[i] = self.m.addVar(vtype=GRB.CONTINUOUS, name=str(c)+'_minimax')
            objective.add(self.obj_vars[i])
            i += 1

        self.m.update()
        self.m.setObjective(objective, GRB.MINIMIZE)
        self.m.update()

    def constructModel(self):
        # Assign n people to each job

        # Do not assign people to overlapping jobs

        # Ensure obj_var is max of sum of duties across class
        i = 0
        for c in self.groups:
            for p in self.personnel:
                if c <= p.tags:
                    self.m.addConstr(quicksum(self.job_vars[p, duty, start, stop, number] for
                                              (p, duty, start, stop, number) in self.x.select(p, '*', '*', '*', '*'))
                                     <= self.obj_vars[i], name='minimax_'+p.id+'_'+str(c))
            i += 1
        pass

    def outputModel(self):
        pass


def main():
    pass

if __name__ == '__main__':
    main()

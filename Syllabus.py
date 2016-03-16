from gurobipy import tuplelist


class Syllabus(object):

    def __init__(self, *initial_data, **kwargs):
        self.syllabus_ID = None
        self.name = None
        self.organization_ID = None
        self.device_type_ID = None
        self.precedence = None
        self.event_arcs = tuplelist()  # Tuplelist of arcs (parent event id, child event id)
        self._ancestors = {}
        self.events = {}  # Set of event objects
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def children(self, e):
        c = set()
        for (i, j) in self.event_arcs.select(e, '*'):
            c.add(j)
        return set([(e, self) for e in c])

    def parents(self, e):
        c = set()
        for (i, j) in self.event_arcs.select('*', e):
            c.add(i)
        return set([(e, self) for e in c])

    # Takes an event e and returns its ancestors
    def ancestors(self, e):
        if e not in self._ancestors:
            parents = self.parents(e)
            self._ancestors[e] = parents
            for p in parents:
                self._ancestors[e] = self.ancestors(p[0]) | self._ancestors[e]

        return self._ancestors[e]
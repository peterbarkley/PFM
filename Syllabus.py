from gurobipy import tuplelist


class Syllabus(object):

    def __init__(self, *initial_data, **kwargs):
        self.syllabus_ID = None
        self.name = None
        self.organization_ID = None
        self.device_type_ID = None
        self.precedence = None
        self.event_arcs = tuplelist()
        self._ancestors = {}
        self.events = set()
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def children(self, e):
        c = set()
        for (i, j) in self.event_arcs.select(e, '*'):
            c.add(j)
        return c

    def parents(self, e):
        c = set()
        for (i, j) in self.event_arcs.select('*', e):
            c.add(i)
        return c

    def ancestors(self, e):
        if e not in self._ancestors:
            self._ancestors[e] = set()
            for p in self.parents(e):
                self._ancestors[e] += self.ancestors(p)

        return self._ancestors[e]
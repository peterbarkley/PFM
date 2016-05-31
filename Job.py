
class Job(object):

    def __init__(self, *initial_data, **kwargs):
            self.shifts = []
            self.btshifts = 0
            self.start = 0
            self.number = 1
            self.between = 24
            self.duties = {}
            for dictionary in initial_data:
                for key in dictionary:
                    setattr(self, key, dictionary[key])
            for key in kwargs:
                setattr(self, key, kwargs[key])
class Constraint(object):
    """Implements Constraint row"""
    def __init__(self, *initial_data, **kwargs):
        self.constraint_ID = None
        self.name = None
        self.subject_resource_type = None
        self.verb = None
        self.positive = None
        self.value = None
        self.object_resource_type = None
        self.object_tag_ID = None
        self.object_resource_ID = None
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __str__(self):
        return "Constraint_" + str(self.constraint_ID)


def main():
    pass

if __name__ == '__main__':
    main()

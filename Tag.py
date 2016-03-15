class Tag(object):
    """Tag class"""

    def __init__(self, *initial_data, **kwargs):
        self.tag_ID = None
        self.name = None
        self.object_tag_ID = None
        self.object_resource_ID = None
        self.expiration = None
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __str__(self):
        print "Tag_" + str(self.name)
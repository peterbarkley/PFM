


class Airfield(object):
    """Implements the airfield class"""

    def __init__(self, *initial_data, **kwargs):
        self.airfield_ID = None
        self.identifier  = None
        self.max_runway_length = None
        self.active = None
        self.latitude = None
        self.longitude = None
        self.elevation = 0
        self.time_zone = None
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])

    # Needs date=datetime.date() and local=Boolean
    def getSun(self, **kwargs):
        from astral import Location
        return Location((self.identifier, None, self.latitude, self.longitude, self.time_zone, self.elevation)).sun(**kwargs)
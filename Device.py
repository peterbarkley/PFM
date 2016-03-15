from Resource import Resource


class Device(Resource):

    def __init__(self, *initial_data, **kwargs):
        self.device_ID = None
        self.category = "Device"
        self.instructor_capacity = 1
        self.student_capacity = 2
        self.passenger_capacity = 0
        self.min_flyer = 1
        super(Device, self).__init__(*initial_data, **kwargs)
        self.id = self.device_ID
        self.resourceType = self.category

    def getPriority(self, wave):
        return 1.0 + wave.planeHours() * (6.0 - self.priority) / 40.0

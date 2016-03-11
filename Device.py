from Resource import Resource

class Device(Resource):

    def __init__(self, *initial_data, **kwargs):
        self.device_ID = None
        self.category = None
        super(Device, self).__init__(*initial_data, **kwargs)
        self.resourceType = "Device"
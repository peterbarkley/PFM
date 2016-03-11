from Squadron import Squadron

class TrainingSquadron(Squadron):

    def __init__(self, *initial_data, **kwargs):
        self.devices = {}
        self.organization_ID = None
        self.forecasts = []
        self.events = {}
        super(TrainingSquadron, self).__init__(*initial_data, **kwargs)

    # Returns the min priority value across forecasts that overlap with w
    def wavePriority(self, w):
        return 1


    def createVariables(self):
        pass

    def constructModel(self):
        pass

    def outputModel(self):
        pass
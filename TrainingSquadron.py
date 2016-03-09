from Squadron import Squadron

class TrainingSquadron(Squadron):

    def __init__(self, *initial_data, **kwargs):
        self.devices = {}
        self.organization_ID = None
        super(TrainingSquadron, self).__init__(*initial_data, **kwargs)

    def createVariables(self):
        pass

    def constructModel(self):
        pass

    def outputModel(self):
        pass
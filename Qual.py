#-------------------------------------------------------------------------------
# Name:        Qual
# Purpose:
#
# Author:      pbarkley
#
# Created:     09/02/2016
# Copyright:   (c) pbarkley 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------


class Qual(object):
    """Implements the qual class"""

    def __init__(self,id):
        self.id = id # Qual name
        self.objectType = None # Lists object of rule (like student for onwing)
        self.object = None # References object of rule (like student for onwing)

    def __str__(self):
        name = "Qual: " + str(self.id)
        if self.object:
            return name + " for " + str(self.objectType) + ' ' + str(self.object)

        return name

    def bind(self,sortie):
        if self.objectType in sortie:
            self.object = sortie[self.objectType]

    def unbind(self):
        self.object = None

    def __eq__(self, other):
        """object_id = None
        other_object_id = None
        if self.object:
            object_id = self.object.id
        if other.object:
            other_object_id = other.object.id
        return (isinstance(other, self.__class__)
                and self.id == other.id
                and self.objectType == other.objectType
                and object_id == other_object_id)"""
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)


    def __ne__(self, other):
        return not self.__eq__(other)


def main():
    pass

if __name__ == '__main__':
    main()

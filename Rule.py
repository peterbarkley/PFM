#-------------------------------------------------------------------------------
# Name:        Rule
# Purpose:
#
# Author:      pbarkley
#
# Created:     26/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------


class Rule(object):
    """Implements the rule class"""

    def __init__(self, id):
        self.id = id # Rule name
        self.positive = True # False if the rule is a negation
        self.subject = None # Resource type of rule subject (like instructor for onwing qual)
        self.qual = None # Qual required by the rule (like 'onwing')
        # self.object = None # Lists object of rule (like student for onwing)
        self.value = None # Numeric value associated with rule
        self.operator = None # String of operator associated with value '<=', '<', etc.

    def __str__(self):
        return "Rule " + str(self.id)


def main():
    pass

if __name__ == '__main__':
    main()

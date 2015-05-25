#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      pbarkley
#
# Created:     28/03/2015
# Copyright:   (c) pbarkley 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

class Resource(object):
    """A squadron resource that can have a sniv"""
    def __init__(self,id):
        self.id = id
        self.snivs = {} #Dictionary of snivs by id
        self._available = {} #Dictionary by day and wave containing whether the resource is available then
        self.resourceType = "Resource"
        self.squadron = None
        self.name = None

    #Returns true if the asset is unavailable on day during wave
    #Takes a date day and a Wave object wave
    def available(self,day,wave):
        #If the lookup has been performed and recorded, give that
        if day in self._available and wave in self._available[day]:
            return self._available[day][wave]
        else:
            self._available[day]={}
            #otherwise, loop through snivs looking
            for s in self.snivs:
                #If any snivs overlap with the wave, resource is unavailable
                if self.resourceType in wave.times:
                    if self.snivs[s].end > wave.times[self.resourceType].begin and self.snivs[s].begin < wave.times[self.resourceType].end:
                        self._available[day][wave]=False
                        return False
                else:
                    if self.snivs[s].end > wave.begin and self.snivs[s].begin < wave.end:
                        self._available[day][wave]=False
                        return False
            self._available[day][wave]=True
            return True

    def __str__(self):
        return self.resourceType+' '+str(self.id)

def main():
    pass

if __name__ == '__main__':
    main()

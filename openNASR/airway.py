from types import SimpleNamespace
    

class Airway(object):
    def __init__(self, airway,NASR):
        if NASR.isAirway(airway):    
            self._addBASE(airway,NASR['AWY_BASE'])
        else:
            print("Unable to find %s"%airway)
            raise 'Airway does not exist in FAA database'    
        
    def _addBASE(self,airway,AWY_BASE):
        self.base = SimpleNamespace( **AWY_BASE[AWY_BASE['AWY_ID']==airway].to_dict(orient='records')[0] )
        # myNASR['APT_BASE'][myNASR['APT_BASE']['ARPT_ID']=='DCA'].to_dict(orient='records')[0]
    
    @property    
    def waypts(self):
        return self.base.AIRWAY_STRING.split(' ')

        
        # print(APT_BASE[APT_BASE[airportIDCol]==airport])
        
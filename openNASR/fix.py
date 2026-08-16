from types import SimpleNamespace
from .basictypes import Raw  

      
class FIX(Raw):
    def __init__(self, fix,NASR):
        if NASR.isFix(fix):    
            print('yes')
            self._addBASE(fix,NASR['FIX_BASE'])
        else:
            print("Unable to find %s"%fix)
            raise 'Fix does not exist in FAA database'    
                    
    def _addBASE(self,fix,FIX_BASE):
        super().__init__(   SimpleNamespace( **FIX_BASE[FIX_BASE['FIX_ID']==fix].to_dict(orient='records')[0] )  ) 
        #self.base = SimpleNamespace( **FIX_BASE[FIX_BASE['FIX_ID']==fix].to_dict(orient='records')[0] )
    
        
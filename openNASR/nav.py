from types import SimpleNamespace
from .basictypes import Raw  

class NAVAID(Raw):
    def __init__(self, navaid,NASR,inCenter=None,inState=None,inCountry=None, navType=None):
        # If there are two NAVAIDs with the same name the first one will be selected
        # unless the state or type is provided.
        if NASR.isNavaid(navaid):    
            self._addBASE(navaid,NASR['NAV_BASE'],inCenter,inState,inCountry, navType)
        else:
            print("Unable to find %s"%navaid)
            raise 'Navaid does not exist in FAA database'    
        
    def _addBASE(self,navaid,NAV_BASE,inCenter=None,inState=None,inCountry=None, navType=None):
        navBool = NAV_BASE['NAV_ID']==navaid
        navCenterBool = (NAV_BASE['HIGH_ALT_ARTCC_ID']==inCenter) | (NAV_BASE['LOW_ALT_ARTCC_ID']==inCenter)
        navStateBool = NAV_BASE['STATE_CODE']==inState
        navCountryBool = NAV_BASE['COUNTRY_NAME']==inCountry
        navTypeBool = NAV_BASE['NAV_TYPE']==navType
        if inCenter is not None:
            navBool = navBool | navCenterBool
        if inState is not None:
            navBool = navBool | navStateBool            
        if inCountry is not None:
            navBool = navBool | navCountryBool
        if navType is not None:
            navBool = navBool | navTypeBool
        navRecs = NAV_BASE[navBool]
        if len(navRecs)>1:
            for idx,cRec in navRecs.iterrows():
                print('----------------------')
                for cKey in ['NAV_ID','NAV_TYPE','HIGH_ALT_ARTCC_ID','LOW_ALT_ARTCC_ID','STATE_CODE','COUNTRY_NAME']:
                    print('%s: %s'%(cKey,cRec[cKey]))
            raise 'More than one Navaid with that name exists in FAA database with criteria specified'
        elif len(navRecs)==1:
            super().__init__(   SimpleNamespace( **NAV_BASE[NAV_BASE['NAV_ID']==navaid].to_dict(orient='records')[0] )  ) 
        else:
            raise 'No Navaid with that name exists in FAA database with criteria specified'
            

    
    # @property    
    # def lat(self):
    #     return self.base.LAT_DECIMAL

    # @property    
    # def lon(self):
    #     return self.base.LONG_DECIMAL
        
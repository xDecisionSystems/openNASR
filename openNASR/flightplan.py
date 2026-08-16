from nasr import NASR
from airport import Airport
from airway import Airway
from fix import Fix
from nav import Nav
from departure import Departure


def identifyElement(fltPlanElement,NASR):
    if NASR.isAirport(fltPlanElement):
        print('Is Airport %s'%fltPlanElement)    
    if NASR.isAirway(fltPlanElement):
        print('Is Airway %s'%fltPlanElement)
    if NASR.isDeparture(fltPlanElement):
        print('Is Departure %s'%fltPlanElement)        
    if NASR.isFix(fltPlanElement):
        print('Is FIX %s'%fltPlanElement)
    if NASR.isNav(fltPlanElement):
        print('Is NAV %s'%fltPlanElement)
    if NASR.isStar(fltPlanElement):
        print('Is STAR %s'%fltPlanElement)

    
def identifyElements(fltPlan,NASR):
    for fltPlanElement in fltPlan:
        print(fltPlanElement)
        identifyElement(fltPlanElement,NASR)


class fltPlan(object):
    def __init__(self,):
        self.fltPlan='KIAH.MMUGS4.LLA.LEV.Y290.GAWKS.FROGZ4.KMIA'
    
    @property
    def elements(self):
        return self.fltPlan.split('.')


            
        
myNASR=NASR()
myAirport=Airport('DCA',myNASR)
myAirway=Airway('Y290',myNASR)
myFIX=Fix('GAWKS',myNASR)
myNAV=Nav('LEV',myNASR)
myDeparture=Departure('MMUGS4',myNASR)



# fp=fltPlan()

# identifyElements(fp.elements,myNASR)

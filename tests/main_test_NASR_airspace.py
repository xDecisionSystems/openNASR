from openNASR import NASR, ARB
myNASR=NASR()

# from nasr.airport import Airport
nas = ARB(myNASR)
zob = nas.getARTCC('ZOB')

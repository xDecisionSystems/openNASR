from openNASR import NASR, Airport
myNASR=NASR()



# from nasr.airport import Airport
BWI = Airport('BWI',myNASR)
DCA = Airport('DCA',myNASR)
# myAirport.ils.getRawByID('01')
# myAirport.rwys.map_ends()
# myAirport.rwy('01')
# myAirport.ils_raw('01')

BWI.plot()

# from math import pi,sin,cos, atan2
# from cfcn import ll2xy
# plt.close('all')
# fig, axs = plt.subplots(1, 2)
# useAirport = BWI
# lonc=useAirport.base.lon
# latc=useAirport.base.lat


# for cRWY in useAirport.rwy.ids:
#     rwyEnds = cRWY.split('/')
#     if len(rwyEnds)==2:
#         lon_start = useAirport.rwyend[rwyEnds[0]].lon
#         lat_start = useAirport.rwyend[rwyEnds[0]].lat
#         lon_end = useAirport.rwyend[rwyEnds[1]].lon
#         lat_end = useAirport.rwyend[rwyEnds[1]].lat
#         axs[1].plot([lon_start,lon_end],[lat_start,lat_end],color='black', linewidth=10)
#         ang = atan2(lat_end-lat_start,lon_end-lon_start)*180/pi
#         print('RWY LL:',cRWY,ang)
        
#         xs,ys =ll2xy([lat_start,lat_end],[lon_start,lon_end],latc=latc,lonc=lonc)[0:2]
#         axs[0].plot(xs,ys,color='black', linewidth=10)
#         ang = atan2(ys[1]-ys[0],xs[1]-xs[0])*180/pi
#         print('RWY xy:',cRWY,ang)



# for cRWY in useAirport.ils.ids:
#     lon =useAirport.ils[cRWY].lon
#     lat =useAirport.ils[cRWY].lat
#     axs[1].scatter(lon,lat,color='red',marker='h')
#     xs,ys =ll2xy(lat,lon,latc=latc,lonc=lonc)[0:2]
#     axs[0].plot(xs,ys,color='red',marker='h') 
    
    

# for cRWY in useAirport.ils.ids:
#     lon =useAirport.ils[cRWY].lon
#     lat =useAirport.ils[cRWY].lat
#     axs[1].scatter(lon,lat,color='blue',marker='x')
#     x,y =ll2xy(lat,lon,latc=latc,lonc=lonc)[0:2]
#     axs[0].plot(x,y,color='blue',marker='x')
#     from matplotlib import pyplot as plt

#     bearing = useAirport.ils[cRWY].trueBearing
#     lonV=lon-.01*cos(pi/2-bearing*pi/180)
#     latV=lat-.01*sin(pi/2-bearing*pi/180)
#     axs[1].plot([lon,lonV],[lat,latV],color='red', linewidth=2)
    
#     ang = 90-bearing
#     xV=x-1*cos(ang*pi/180)
#     yV=y-1*sin(ang*pi/180)    
#     axs[0].plot([x,xV],[y,yV],color='blue',marker='x')
#     print('ILS:',cRWY, ang)

        
# plt.gca().set_aspect('equal')

from numpy import radians, cos, sin, median, radians, sqrt, percentile, float64, array, matmul, generic, ndarray, arctan2, arcsin,degrees
import time


def ll2xy(lats,lons, latc=None, lonc=None, llc=None):
    # See https://en.wikipedia.org/wiki/Earth_radius#Equatorial_radius
    lats=radians(lats)
    lons=radians(lons)      
    if llc is not None:
        latc=radians(llc[0])
        lonc=radians(llc[1])
    elif latc is not None and lonc is not None and llc is None:
        latc=radians(latc)
        lonc=radians(lonc)
    else:
        latc=median(lats)
        lonc=median(lons)
        
    earthRad=radiusOfEarth(latc)
    cosc=sin(latc)*sin(lats)+cos(latc)*cos(lats)*cos(lons-lonc)
    
    x=earthRad*( cos(lats)*sin(lons-lonc) ) / cosc
    y=earthRad*( cos(latc)*sin(lats)-sin(latc)*cos(lats)*cos(lons-lonc) ) /cosc
    dist=sqrt(x**2+y**2)

    return x,y,array([latc,lonc]),dist

def xy2ll(x,y, latc=None, lonc=None, llc=None):
    """
    Inverse of the gnomic projection. Converts projected (x, y) coordinates back to latitudes and longitudes.
    
    Parameters:
        center_lat (float): Central latitude in degrees.
        center_lon (float): Central longitude in degrees.
        x (array): Array of x-coordinates from the gnomic projection.
        y (array): Array of y-coordinates from the gnomic projection.
    
    Returns:
        latitudes, longitudes (arrays): Arrays of latitudes and longitudes in degrees.
    """
    if llc is not None:
        latc=radians(llc[0])
        lonc=radians(llc[1])
    elif latc is not None and lonc is not None and llc is None:
        latc=radians(latc)
        lonc=radians(lonc)
    
    # Calculate the Earth's radius at the central latitude
    R_center = radiusOfEarth(latc)
    # Calculate rho (distance from the center of the projection)
    rho = sqrt(x**2 + y**2)
    # Calculate the angular distance c
    c = arctan2(rho, R_center)
    
    # Inverse formulas for latitude and longitude
    sin_c = sin(c)
    cos_c = cos(c)
    
    latitudes_rad = arcsin(cos_c * sin(latc) + (y * sin_c * cos(latc)) / rho)
    longitudes_rad = lonc + arctan2(x * sin_c, rho * cos(latc) * cos_c - y * sin(latc) * sin_c)
    
    # Convert radians back to degrees
    latitudes = degrees(latitudes_rad)
    longitudes = degrees(longitudes_rad)
    
    return latitudes, longitudes


def radiusOfEarth(latitude):
    """
    Calculate the Earth's radius at a specific latitude.
    
    Parameters:
        latitude (float): Latitude in radians.
        
    Returns:
        float: Earth's radius at the given latitude in kilometers.
    """
    eqRad=3443.91847352  # Radius [NM] at the equator
    eqPol=3432.37169102   # Radius [NM] at the polar 
    eqNum = (eqRad*eqRad*cos(latitude))**2+(eqPol*eqPol*sin(latitude))**2
    eqDon = (eqRad*cos(latitude))**2+(eqPol*sin(latitude))**2
    earthRad=sqrt(eqNum/eqDon)
    return earthRad

def calcAngle(heading):
    return 90-heading
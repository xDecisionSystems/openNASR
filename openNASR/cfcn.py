from numpy import radians, cos, sin, median, radians, sqrt, percentile, float64, array, matmul, generic, ndarray, arctan2, arcsin,degrees, where, asarray, any as np_any, isfinite
import time


def _validate_latlon(latitudes, longitudes):
    latitudes = asarray(latitudes)
    longitudes = asarray(longitudes)
    if np_any(~isfinite(latitudes)) or np_any((latitudes < -90) | (latitudes > 90)):
        raise ValueError("latitude must be finite and between -90 and 90 degrees")
    if np_any(~isfinite(longitudes)) or np_any((longitudes < -180) | (longitudes > 180)):
        raise ValueError("longitude must be finite and between -180 and 180 degrees")


def ll2xy(lats,lons, latc=None, lonc=None, llc=None):
    """Project latitude/longitude inputs around a ``(latitude, longitude)`` center.

    Geographic pairs and ``llc`` always use latitude first, longitude second.
    Returned planar values are ``(x/east, y/north)`` in nautical miles.
    """
    # See https://en.wikipedia.org/wiki/Earth_radius#Equatorial_radius
    _validate_latlon(lats, lons)
    lats=radians(lats)
    lons=radians(lons)      
    if llc is not None:
        _validate_latlon(llc[0], llc[1])
        latc=radians(llc[0])
        lonc=radians(llc[1])
    elif latc is not None and lonc is not None and llc is None:
        _validate_latlon(latc, lonc)
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
    Inverse projection returning ``(latitude, longitude)``.

    ``llc`` and separate center arguments use latitude first, longitude second;
    planar input is ``(x/east, y/north)`` in nautical miles.
    
    Parameters:
        center_lat (float): Central latitude in degrees.
        center_lon (float): Central longitude in degrees.
        x (array): Array of x-coordinates from the gnomic projection.
        y (array): Array of y-coordinates from the gnomic projection.
    
    Returns:
        latitudes, longitudes (arrays): Arrays of latitudes and longitudes in degrees.
    """
    if llc is not None:
        _validate_latlon(llc[0], llc[1])
        latc=radians(llc[0])
        lonc=radians(llc[1])
    elif latc is not None and lonc is not None and llc is None:
        _validate_latlon(latc, lonc)
        latc=radians(latc)
        lonc=radians(lonc)
    
    # Calculate the Earth's radius at the central latitude
    R_center = radiusOfEarth(latc)
    # Calculate rho (distance from the center of the projection)
    rho = sqrt(x**2 + y**2)
    safe_rho = where(rho == 0, 1.0, rho)
    # Calculate the angular distance c
    c = arctan2(rho, R_center)
    
    # Inverse formulas for latitude and longitude
    sin_c = sin(c)
    cos_c = cos(c)
    
    latitudes_rad = arcsin(cos_c * sin(latc) + (y * sin_c * cos(latc)) / safe_rho)
    longitudes_rad = lonc + arctan2(x * sin_c, safe_rho * cos(latc) * cos_c - y * sin(latc) * sin_c)
    latitudes_rad = where(rho == 0, latc, latitudes_rad)
    longitudes_rad = where(rho == 0, lonc, longitudes_rad)
    
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

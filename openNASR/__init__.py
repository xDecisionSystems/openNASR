from .nasr import NASR as NASR
from .airport import Airport as Airport
from .arb import ARB as ARB
from .airspace import ClassAirspace as ClassAirspace
from .airspace import ClassAirspaceRepository as ClassAirspaceRepository
from .atc import AtcFacility as AtcFacility
from .atc import AtcFacilityRepository as AtcFacilityRepository
from .atc import Radar as Radar
from .atc import RadarRepository as RadarRepository
from .airway import Airway as Airway
from .airway import AirwayRepository as AirwayRepository
from .communications import CommunicationOutlet as CommunicationOutlet
from .communications import (
    CommunicationOutletRepository as CommunicationOutletRepository,
)
from .communications import Frequency as Frequency
from .communications import FrequencyRepository as FrequencyRepository
from .fix import FIX as FIX
from .military import MilitaryOperation as MilitaryOperation
from .military import MilitaryOperationRepository as MilitaryOperationRepository
from .fss import FlightServiceStation as FlightServiceStation
from .fss import FlightServiceStationRepository as FlightServiceStationRepository
from .locations import LocationIdentifier as LocationIdentifier
from .locations import LocationIdentifierRepository as LocationIdentifierRepository
from .weather import AutomatedWeatherStation as AutomatedWeatherStation
from .weather import (
    AutomatedWeatherStationRepository as AutomatedWeatherStationRepository,
)
from .weather import WeatherLocation as WeatherLocation
from .weather import WeatherLocationRepository as WeatherLocationRepository
from .holding import HoldingPattern as HoldingPattern
from .holding import HoldingPatternRepository as HoldingPatternRepository
from .nav import NAVAID as NAVAID
from .records import ClassAirspaceRecord as ClassAirspaceRecord
from .records import AirwayRecord as AirwayRecord
from .records import AirwaySegmentRecord as AirwaySegmentRecord
from .records import AtcFacilityRecord as AtcFacilityRecord
from .records import AtcRemarkRecord as AtcRemarkRecord
from .records import AtcServiceRecord as AtcServiceRecord
from .records import AtisRecord as AtisRecord
from .records import AutomatedWeatherStationRecord as AutomatedWeatherStationRecord
from .records import FlightServiceStationRecord as FlightServiceStationRecord
from .records import (
    FlightServiceStationRemarkRecord as FlightServiceStationRemarkRecord,
)
from .records import LocationIdentifierRecord as LocationIdentifierRecord
from .records import RadarRecord as RadarRecord
from .records import WeatherLocationRecord as WeatherLocationRecord
from .records import WeatherServiceRecord as WeatherServiceRecord
from .records import CommunicationOutletRecord as CommunicationOutletRecord
from .records import FrequencyRecord as FrequencyRecord
from .records import HoldingPatternChartRecord as HoldingPatternChartRecord
from .records import HoldingPatternRecord as HoldingPatternRecord
from .records import HoldingPatternRemarkRecord as HoldingPatternRemarkRecord
from .records import (
    HoldingPatternSpeedAltitudeRecord as HoldingPatternSpeedAltitudeRecord,
)
from .records import MilitaryOperationRecord as MilitaryOperationRecord
from .cycles import notify_if_update_available

__all__ = [
    "ARB",
    "Airway",
    "AirwayRecord",
    "AirwayRepository",
    "AirwaySegmentRecord",
    "AtcFacility",
    "AtcFacilityRecord",
    "AtcFacilityRepository",
    "AtcRemarkRecord",
    "AtcServiceRecord",
    "AtisRecord",
    "AutomatedWeatherStation",
    "AutomatedWeatherStationRecord",
    "AutomatedWeatherStationRepository",
    "Airport",
    "ClassAirspace",
    "ClassAirspaceRecord",
    "ClassAirspaceRepository",
    "CommunicationOutlet",
    "CommunicationOutletRecord",
    "CommunicationOutletRepository",
    "FIX",
    "Frequency",
    "FrequencyRecord",
    "FrequencyRepository",
    "FlightServiceStation",
    "FlightServiceStationRecord",
    "FlightServiceStationRemarkRecord",
    "FlightServiceStationRepository",
    "HoldingPattern",
    "HoldingPatternChartRecord",
    "HoldingPatternRecord",
    "HoldingPatternRemarkRecord",
    "HoldingPatternRepository",
    "HoldingPatternSpeedAltitudeRecord",
    "MilitaryOperation",
    "MilitaryOperationRecord",
    "MilitaryOperationRepository",
    "LocationIdentifier",
    "LocationIdentifierRecord",
    "LocationIdentifierRepository",
    "NASR",
    "NAVAID",
    "Radar",
    "RadarRecord",
    "RadarRepository",
    "WeatherLocation",
    "WeatherLocationRecord",
    "WeatherLocationRepository",
    "WeatherServiceRecord",
]

notify_if_update_available()

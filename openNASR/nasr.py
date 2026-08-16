from pathlib import Path
from datetime import datetime
from warnings import warn
from zipfile import ZipFile
from pandas import read_csv
from .arb import ARB
from .exceptions import CycleNotFoundError, SchemaMismatchError
from .registry import TableRegistry
from .schemas import SCHEMA_SUFFIX, SchemaCatalog
import calendar
# from .airport import AIRPORT

def timestampToYearDecimal(useDate):
    # Convert the timestamp to a datetime object
    dt = datetime.strptime(useDate, '%Y-%m-%d')
    # Extract the year, month, and day
    year = dt.year
    month = dt.month
    day = dt.day

    # Calculate the total number of days in the year
    if calendar.isleap(year):
        days_in_year = 366
    else:
        days_in_year = 365
    # Calculate the day of the year
    day_of_year = (dt - datetime(year, 1, 1)).days + 1

    # Calculate the year in decimal format
    year_decimal = year + (day_of_year - 1) / days_in_year
    return year_decimal



class NASR(dict):
    def __init__(self,useDate=None,update=False,preloadAll=False,diagnostic=False):
        if preloadAll:
            raise NotImplementedError("preloadAll is not yet supported")
        if update:
            # Code here will download new NASR data from FAA.
            pass
        self.__diagnostic = diagnostic
        self.setupFiles(useDate)



    def setupFiles(self,useDate):
        self.__module_fd=Path(__file__).parent
        self.__data_zip_fd = self.__module_fd.joinpath('data/zip')
        self.__data_fd = self.__module_fd.joinpath('data/uncompressed')

        NASRZipPaths=list(self.__data_zip_fd.glob('*.zip'))
        availableZips=[cFile.name for cFile in NASRZipPaths]
        availableZips.sort()
        availableDates=[cFile.stem.split('_')[-1] for cFile in NASRZipPaths]
        if not availableDates:
            self._raise_cycle_not_found(useDate)

        if useDate is None:
            useDate = availableDates[-1]
            useDateZip = availableZips[-1]
        else:
            requestedDate = useDate
            earlierDates = [(cZip,cDate) for cZip, cDate in zip(availableZips,availableDates) if cDate<=useDate]
            if not earlierDates:
                self._raise_cycle_not_found(useDate)
            useDateZip,useDate = earlierDates[-1]
            if useDate != requestedDate:
                warn(
                    "NASR database does not exist for %s; using %s instead"
                    % (requestedDate, useDate),
                    stacklevel=2,
                )

        self.__useDate = useDate
        self.__useDateZip = self.__data_zip_fd.joinpath( useDateZip )
        self.__useDateFolder = self.__data_fd.joinpath( self.__useDateZip.stem )
        self.checkForDecompressed()
        self.loadCSVData()

    def _raise_cycle_not_found(self, requested_date):
        requested = f" for requested date {requested_date}" if requested_date else ""
        raise CycleNotFoundError(
            f"No NASR cycle found{requested} in {self.__data_zip_fd}. "
            "Add a 28DaySubscription_Effective_YYYY-MM-DD.zip file to that directory."
        )

    @property
    def yearDecimal(self):
        return timestampToYearDecimal(self.__useDate)


    def checkForDecompressed(self):
        if not self.__useDateFolder.exists():
            warn(
                "NASR archive is being decompressed: %s" % self.__useDateZip,
                stacklevel=2,
            )
            with ZipFile(self.__useDateZip,'r') as zObject:
                zObject.extractall(self.__useDateFolder)

        CSVPath=self.__useDateFolder.joinpath('CSV_Data/')
        CSVDecompressedFolder=[cPath for cPath in CSVPath.glob('*/') if cPath.is_dir()]
        if len(CSVDecompressedFolder):
            self.__useDateCSVFolder=CSVDecompressedFolder[0]
        else:
            zipFilePath=list(CSVPath.glob('*.zip'))[0]
            FilePathOut=CSVPath.joinpath(zipFilePath.name.split('.')[0])
            with ZipFile(zipFilePath,'r') as zObject:
                zObject.extractall(FilePathOut)
            self.__useDateCSVFolder=FilePathOut

    def loadCSVData(self):
        csv_files = sorted(self.__useDateCSVFolder.glob('*.csv'))
        schema_files = [
            path for path in csv_files if path.stem.endswith(SCHEMA_SUFFIX)
        ]
        catalog = None
        registry = None
        if schema_files:
            catalog = SchemaCatalog()
            self.schema_id = catalog.identify_schema(self.__useDateCSVFolder)
            registry = TableRegistry(catalog=catalog)
            operational_names = [
                path.stem
                for path in csv_files
                if not path.stem.endswith(SCHEMA_SUFFIX)
            ]
            registry.require_modeled(
                operational_names,
                cycle=self.__useDate,
                diagnostic=self.__diagnostic,
            )

        for cFile in csv_files:
            dfName=cFile.name.split('.')[0]
            read_options = {}
            if catalog is not None:
                read_options = {
                    "dtype": str,
                    "keep_default_na": False,
                    "na_filter": False,
                }
            try:
                self[dfName]=read_csv(cFile,index_col=False,**read_options)
            except Exception as error:
                # handle the exception
                warn(
                    "Unable to read %s with the default CSV decoder (%s); retrying "
                    "with encoding_errors='backslashreplace'." % (cFile, error),
                    stacklevel=2,
                )
                self[dfName]=read_csv(
                    cFile,
                    index_col=False,
                    encoding_errors='backslashreplace',
                    **read_options,
                )
            if catalog is not None and not dfName.endswith(SCHEMA_SUFFIX):
                if dfName in registry.supported_tables():
                    report = catalog.validate(dfName, self[dfName], self.schema_id)
                    if not self.__diagnostic:
                        table_spec = registry.table(dfName)
                        report.require_compatible(
                            cycle=self.__useDate,
                            table_spec=table_spec,
                            record_class=table_spec.record_type,
                        )

        if "APT_BASE" in self and "ARPT_ID" not in self["APT_BASE"].columns:
            raise SchemaMismatchError(
                "APT_BASE is missing required identifier column ARPT_ID",
                cycle=self.__useDate,
                table="APT_BASE",
                missing_columns=("ARPT_ID",),
            )


    def isAirport(self,airport : str, forceFAA: bool = True):
        """Return whether an airport exists and its matched identifier details.

        Returns ``(exists, matched_column, faa_identifier)``. When
        ``forceFAA`` is true, related-table callers receive ``ARPT_ID`` as the
        matched column and the FAA identifier as the lookup value.
        """
        isAirportBool = False
        airportIDCol = None
        ARPT_ID = None
        for useCol in ['ARPT_ID', 'ICAO_ID']:
            if any(self['APT_BASE'][useCol]==airport):
                isAirportBool=True
                airportIDCol = useCol
                ARPT_ID = self['APT_BASE'][self['APT_BASE'][useCol]==airport]['ARPT_ID'].tolist()[0]
                break
        if forceFAA:
            airportIDCol='ARPT_ID'
        return isAirportBool,airportIDCol, ARPT_ID

    def isAirway(self,airway  : str):
        return airway in self['AWY_BASE']['AWY_ID'].to_list()

    def isDeparture(self, departure : str):
        return departure in self['DP_BASE']['DP_COMPUTER_CODE'].apply(lambda dpCode: dpCode.split('.')[0]).to_list()

    def isFix(self,fix : str):
        return fix in self['FIX_BASE']['FIX_ID'].to_list()

    def isNavaid(self,nav : str):
        return nav in self['NAV_BASE']['NAV_ID'].to_list()

    def isStar(self, star : str):
        return star in self['STAR_BASE']['STAR_COMPUTER_CODE'].apply(lambda starCode: starCode.split('.')[1]).to_list()

    def loadARTCC(self):
        self.artcc = ARB(self)

    # def loadAirports(self):
    #     self.airports = AIRPORT(self['ARB_BASE'],self['ARB_SEG'],arbType='ARTCC')

# myNASR=NASR()

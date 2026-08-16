from pathlib import Path
from datetime import datetime
from warnings import warn
from zipfile import ZipFile 
from pandas import read_csv
from .arb import ARB
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
    def __init__(self,useDate=None,update=False,preloadAll=False):
        if update:
            # Code here will download new NASR data from FAA.
            pass
        self.setupFiles(useDate)
        if preloadAll==True:
            # THIS WILL BREAK.  NOT SETUP YET
            self.loadARTCC()
            self.loadAirports()
            

                
    def setupFiles(self,useDate):
        self.__module_fd=Path(__file__).parent
        self.__data_zip_fd = self.__module_fd.joinpath('data/zip')
        self.__data_fd = self.__module_fd.joinpath('data/uncompressed')

        NASRZipPaths=list(self.__data_zip_fd.glob('*.zip'))
        availibleZips=[cFile.name for cFile in NASRZipPaths]
        availibleZips.sort()
        availibleDates=[cFile.stem.split('_')[-1] for cFile in NASRZipPaths]
    
        if useDate is None:
            useDate = availibleDates[-1]
            useDateZip = availibleZips[-1]
        else:
            earlierDates = [(cZip,cDate) for cZip, cDate in zip(availibleZips,availibleDates) if cDate<useDate]
            useDateZip,useDate = earlierDates[-1]
            # self.useDateFolder=NASRPath.joinpath(earlierDates[-1])
            warnStr="NASR database does not exist for %s; using %s instead"%(useDate,earlierDates[-1])
            warn(warnStr) 
            
        self.__useDate = useDate
        self.__useDateZip = self.__data_zip_fd.joinpath( useDateZip )   
        self.__useDateFolder = self.__data_fd.joinpath( self.__useDateZip.stem )
        self.checkForDecompressed()
        self.loadCSVData()

    @property
    def yearDecimal(self):
        return timestampToYearDecimal(self.__useDate)
        

    def checkForDecompressed(self):
        if not self.__useDateFolder.exists():
            print('NASR Zip file beginning to decompress.')
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
        for cFile in self.__useDateCSVFolder.glob('*.csv'): 
            dfName=cFile.name.split('.')[0]
            try:
                self[dfName]=read_csv(cFile,index_col=False)
            except Exception as error:
                # handle the exception
                print('-----------------------------')
                print('Error reading csv data, likely due to incorrect data or encodeing\nTrying again using backslashreplace fro encoding_errors')
                print(cFile)
                print(error) # An exception occurred: division by zero
                self[dfName]=read_csv(cFile,index_col=False, encoding_errors='backslashreplace')
                print('-----------------------------')

    
    def isAirport(self,airport : str, forceFAA: bool):
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
        self.artcc = ARB(self['ARB_BASE'],self['ARB_SEG'],arbType='ARTCC')

    # def loadAirports(self):
    #     self.airports = AIRPORT(self['ARB_BASE'],self['ARB_SEG'],arbType='ARTCC')    
        
# myNASR=NASR()

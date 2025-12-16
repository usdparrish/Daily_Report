import os
import csv
import datetime
from datetime import timedelta
from calendar import monthrange
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import numpy as np
import pyodbc

#os.chdir('')
cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))
#network_path = r'\\server4.rrc.center\public\dashboards\dailyreport'
#os.chdir(network_path)
conn = pyodbc.connect('Driver={SQL Server};'
        'Server=PHISQL1.rrc.center;'
        'Database=RRC_Daily_Report;'
        'Trusted_Connectio=yes;')
c = conn.cursor()

output_file= os.path.join(app_path,r'output\forecast.csv')
f = open(output_file,'w+',newline='')

class Forecast: 
   
  def __init__(self,month,year):
    self.month = int(month)
    self.year = int(year)

  #Location,Modality as ProcedureCategory,Month,Year,ProjectedVolume,Days,ProjectedDailyVolume as Unit
  def monthforecastcsv(self):
    sql_query =('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Month,ProjectedVolume FROM forecast''')
    #sql_query =('''SELECT Location,Modality as ProcedureCategory,Year,Month,ProjectedDailyVolume as Unit FROM forecast''') #uncmoment for ProjectedDailyVolume
    df=pd.read_sql_query(sql_query,conn)
  
    forecastdf = df.copy(deep=False)
    forecastdf['Month'] = forecastdf['Year'].map(str) + '-' + forecastdf['Month'].map(str)
    forecastdf['Quarter'] = pd.PeriodIndex(pd.to_datetime(forecastdf['Month']),freq='Q')
  
    forecastdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
    #return forecastdf

  def getmonthforecastdf(self):
    sql_query =('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Month,ProjectedVolume FROM forecast''')
    df=pd.read_sql_query(sql_query,conn)
  
    forecastdf = df.copy(deep=False)
    forecastdf = forecastdf[forecastdf['Year'] == self.year]
    forecastdf = forecastdf[forecastdf['Month'] == self.month]
    #forecastdf['Year'] = 'forecast'  #'{}/{} forecast'.format(input_month,input_year)
  
    print(forecastdf)
    return forecastdf
    
  def getquarterforecastdf(self,iquarter):
    sql_query =('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Year||"-"||Month,ProjectedVolume,Locations.Region 
              FROM forecast INNER JOIN LOCATIONS on forecast.Location = Locations.LocationName''')
    df=pd.read_sql_query(sql_query,conn)
    
    df['Quarter'] = pd.to_datetime(df['Month']).dt.quarter
    forecastdf = df.copy(deep=False)
  
    forecastdf = forecastdf[forecastdf['Year'] == self.year]
    forecastdf = forecastdf[forecastdf['Quarter'] == iquarter]
    forecastdf['Year'] = 'Forecast'  #'{}/{} forecast'.format(input_month,input_year)
    forecastdf['Volume'] = forecastdf['Volume']
  
    #print(forecastdf)
    return forecastdf 

  def dailyforecast(self):
    sql_query =('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Month,ProjectedVolume FROM forecast''')
    #sql_query =('''SELECT Location,Year,Month,ProjectedDailyVolume as Unit FROM forecast''') #uncmoment for ProjectedDailyVolume
    df=pd.read_sql_query(sql_query,conn)
  
    forecastdf = df.copy(deep=False)
    forecastdf['Month'] = forecastdf['Year'].map(str) + '-' + forecastdf['Month'].map(str)
    forecastdf['Quarter'] = pd.PeriodIndex(pd.to_datetime(forecastdf['Month']),freq='Q')
  
    forecastdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
    #return forecastdf

  def getforecastdf(self):
    sql_query =('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Month,ProjectedDailyVolume as Unit,Locations.Region 
            FROM forecast INNER JOIN LOCATIONS on forecast.Location = Locations.LocationName''')
    df=pd.read_sql_query(sql_query,conn)
  
    forecastdf = df.copy(deep=False)
    forecastdf = forecastdf[forecastdf['Year'] == self.year]
    forecastdf = forecastdf[forecastdf['Month'] == self.month]
    forecastdf['Year'] = 'Forecast'  #'{}/{} forecast'.format(input_month,input_year)
  
    #print(forecastdf)
    return forecastdf

  def getforecastvolume(self):
    sql_query =('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Month,ProjectedDailyVolume as Unit,Locations.Region 
            FROM forecast INNER JOIN LOCATIONS on forecast.Location = Locations.LocationName''')
    df=pd.read_sql_query(sql_query,conn)
  
    forecastdf = df.copy(deep=False)
    forecastdf = forecastdf[forecastdf['Year'] == self.year]
    forecastdf = forecastdf[forecastdf['Month'] == self.month]
    return forecastdf['Volume']

  def getMTDforecast(self,businessdays):
    sql_query = ('''SELECT Location as LocationName,Modality as ProcedureCategory,Year,Month,ProjectedDailyVolume as Unit,Locations.Region 
            FROM forecast INNER JOIN LOCATIONS on forecast.Location = Locations.LocationName''')
    df=pd.read_sql_query(sql_query,conn)
    
    forecastdf = df.copy(deep=False)
    forecastdf = forecastdf[forecastdf['Year'] == self.year]
    forecastdf = forecastdf[forecastdf['Month'] == self.month]
    forecastdf['Year'] = 'Forecast'  #'{}/{} forecast'.format(input_month,input_year)
    forecastdf['Unit'] = forecastdf['Unit'] * businessdays
  
    #print(forecastdf)
    return forecastdf

  def getYTDforecast(self,year):
    sql_query =(f'''SELECT b.MONTH,b.YEAR,b.Location,l.Region,b.Modality as ProcedureCategory,
b.ProjectedDailyVolume as Unit,d.Days,Sum(ProjectedDailyVolume * d.Days) as Forecast
FROM forecast b

INNER JOIN Locations l ON b.Location = l.LocationName

INNER JOIN (

SELECT Mnth,Yr,LocationName,Count(*) as Days
FROM (
  SELECT Daily.ScheduleStartDate,datepart(month,Daily.ScheduleStartDate) as Mnth,
    datepart(year,Daily.ScheduleStartDate) as Yr, Daily.LocationName
  FROM DAILY
  WHERE --NO SATURDAY
    (datepart(year,ScheduleStartDate) = {year} and datepart(weekday,Daily.ScheduleStartDate) != 7)
  GROUP BY Daily.ScheduleStartDate, datepart(month,Daily.ScheduleStartDate),
    datepart(year,Daily.ScheduleStartDate),LocationName)
GROUP BY Mnth,Yr,LocationName) d

ON b.Month = d.Mnth AND b.Year = d.Yr AND b.Location = d.LocationName

LEFT JOIN (

SELECT datepart(month,Daily.ScheduleStartDate) as Mnth,
  datepart(year,Daily.ScheduleStartDate) as Yr, Daily.LocationName,Daily.ProcedureCategory,
  Sum(Volume)as Unit
FROM DAILY
WHERE --NO SATURDAY
  (datepart(year,ScheduleStartDate) = {year}
  AND ProcedureCategory != "E&M CODES" AND ProcedureCategory != "ENHANCED SRVC")

GROUP BY datepart(month,Daily.ScheduleStartDate),
  datepart(year,Daily.ScheduleStartDate),LocationName,ProcedureCategory
) dv

ON b.Month = dv.Mnth AND b.Year = dv.Yr AND b.Location = dv.LocationName AND b.Modality as ProcedureCategory = dv.ProcedureCategory

WHERE b.YEAR = {year}
GROUP BY b.MONTH,b.YEAR,b.Location,b.Modality as ProcedureCategory''')
    df=pd.read_sql_query(sql_query,conn)
    
    return df
#bt = forecast()
#bt.dailyforecast()
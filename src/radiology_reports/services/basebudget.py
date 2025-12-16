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
import sqlite3


#os.chdir('')
cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))
#network_path = r'\\server4.rrc.center\public\dashboards\dailyreport'
#os.chdir(network_path)
conn = sqlite3.connect('Daily_SQLite3.db')
c = conn.cursor() # The database will be saved in the location where your 'py' file is saved

output_file= os.path.join(app_path,r'output\basebudget.csv')
f = open(output_file,'w+',newline='')

class BaseBudget: 
   
  def __init__(self,month,year):
    self.month = int(month)
    self.year = int(year)

  #Location,Modality,Month,Year,ProjectedVolume,Days,ProjectedDailyVolume
  def monthbasebudgetcsv(self):
    c.execute('''SELECT Location,Modality,Year,Month,ProjectedVolume FROM basebudget''')
    #c.execute('''SELECT Location,Modality,Year,Month,ProjectedDailyVolume FROM basebudget''') #uncmoment for ProjectedDailyVolume
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit'])
  
    basebudgetdf = df.copy(deep=False)
    basebudgetdf['Month'] = basebudgetdf['Year'].map(str) + '-' + basebudgetdf['Month'].map(str)
    basebudgetdf['Quarter'] = pd.PeriodIndex(pd.to_datetime(basebudgetdf['Month']),freq='Q')
  
    basebudgetdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
    #return basebudgetdf

  def getmonthbasebudgetdf(self):
    c.execute('''SELECT Location,Modality,Year,Month,ProjectedVolume FROM basebudget''')
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit'])
  
    basebudgetdf = df.copy(deep=False)
    basebudgetdf = basebudgetdf[basebudgetdf['Year'] == self.year]
    basebudgetdf = basebudgetdf[basebudgetdf['Month'] == self.month]
    #basebudgetdf['Year'] = 'basebudget'  #'{}/{} basebudget'.format(input_month,input_year)
  
    print(basebudgetdf)
    return basebudgetdf
    
  def getquarterbasebudgetdf(self,iquarter):
    c.execute('''SELECT Location,Modality,Year,Year||"-"||Month,ProjectedVolume,Locations.Region 
              FROM basebudget INNER JOIN LOCATIONS on basebudget.Location = Locations.LocationName''')
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit','Region'])
    df['Quarter'] = pd.to_datetime(df['Month']).dt.quarter
    basebudgetdf = df.copy(deep=False)
  
    basebudgetdf = basebudgetdf[basebudgetdf['Year'] == self.year]
    basebudgetdf = basebudgetdf[basebudgetdf['Quarter'] == iquarter]
    basebudgetdf['Year'] = 'BaseBudget'  #'{}/{} basebudget'.format(input_month,input_year)
    basebudgetdf['Unit'] = basebudgetdf['Unit']
  
    #print(basebudgetdf)
    return basebudgetdf 

  def dailybasebudget(self):
    c.execute('''SELECT Location,Modality,Year,Month,ProjectedVolume FROM basebudget''')
    #c.execute('''SELECT Location,Year,Month,ProjectedDailyVolume FROM basebudget''') #uncmoment for ProjectedDailyVolume
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit'])
  
    basebudgetdf = df.copy(deep=False)
    basebudgetdf['Month'] = basebudgetdf['Year'].map(str) + '-' + basebudgetdf['Month'].map(str)
    basebudgetdf['Quarter'] = pd.PeriodIndex(pd.to_datetime(basebudgetdf['Month']),freq='Q')
  
    basebudgetdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
    #return basebudgetdf

  def getbasebudgetdf(self):
    c.execute('''SELECT Location,Modality,Year,Month,ProjectedDailyVolume,Locations.Region 
            FROM basebudget INNER JOIN LOCATIONS on basebudget.Location = Locations.LocationName''')
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit','Region'])
  
    basebudgetdf = df.copy(deep=False)
    basebudgetdf = basebudgetdf[basebudgetdf['Year'] == self.year]
    basebudgetdf = basebudgetdf[basebudgetdf['Month'] == self.month]
    basebudgetdf['Year'] = 'BaseBudget'  #'{}/{} basebudget'.format(input_month,input_year)
  
    #print(basebudgetdf)
    return basebudgetdf

  def getbasebudgetvolume(self):
    c.execute('''SELECT Location,Modality,Year,Month,ProjectedDailyVolume,Locations.Region 
            FROM basebudget INNER JOIN LOCATIONS on basebudget.Location = Locations.LocationName''')
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit','Region'])
  
    basebudgetdf = df.copy(deep=False)
    basebudgetdf = basebudgetdf[basebudgetdf['Year'] == self.year]
    basebudgetdf = basebudgetdf[basebudgetdf['Month'] == self.month]
    return basebudgetdf['Unit']

  def getMTDbasebudget(self,businessdays):
    c.execute('''SELECT Location,Modality,Year,Month,ProjectedDailyVolume,Locations.Region 
            FROM basebudget INNER JOIN LOCATIONS on basebudget.Location = Locations.LocationName''')
    df = pd.DataFrame(c.fetchall(), columns=['LocationName','ProcedureCategory','Year','Month','Unit','Region'])
    
    basebudgetdf = df.copy(deep=False)
    basebudgetdf = basebudgetdf[basebudgetdf['Year'] == self.year]
    basebudgetdf = basebudgetdf[basebudgetdf['Month'] == self.month]
    basebudgetdf['Year'] = 'BaseBudget'  #'{}/{} basebudget'.format(input_month,input_year)
    basebudgetdf['Unit'] = basebudgetdf['Unit'] * businessdays
  
    #print(basebudgetdf)
    return basebudgetdf

  def getYTDbasebudget(self,year):
    c.execute(f'''SELECT b.MONTH,b.YEAR,b.Location,l.Region,b.Modality,
b.ProjectedDailyVolume,d.Days,Sum(ProjectedDailyVolume * d.Days) as basebudget
FROM basebudget b

INNER JOIN Locations l ON b.Location = l.LocationName

INNER JOIN (

SELECT Mnth,Yr,LocationName,Count(*) as Days
FROM (
  SELECT Daily.ScheduleStartDate,strftime('%m',Daily.ScheduleStartDate) as Mnth,
    strftime('%Y',Daily.ScheduleStartDate) as Yr, Daily.LocationName
  FROM DAILY
  WHERE --NO SATURDAY
    (strftime('%Y',ScheduleStartDate) = "{year}" and strftime('%w',Daily.ScheduleStartDate) != "6")
  GROUP BY Daily.ScheduleStartDate, strftime('%m',Daily.ScheduleStartDate),
    strftime('%Y',Daily.ScheduleStartDate),LocationName)
GROUP BY Mnth,Yr,LocationName) d

ON b.Month = d.Mnth AND b.Year = d.Yr AND b.Location = d.LocationName

LEFT JOIN (

SELECT strftime('%m',Daily.ScheduleStartDate) as Mnth,
  strftime('%Y',Daily.ScheduleStartDate) as Yr, Daily.LocationName,Daily.ProcedureCategory,
  Sum(Unit) as Volume
FROM DAILY
WHERE --NO SATURDAY
  (strftime('%Y',ScheduleStartDate) = "{year}"
  AND ProcedureCategory != "E&M CODES" AND ProcedureCategory != "ENHANCED SRVC")

GROUP BY strftime('%m',Daily.ScheduleStartDate),
  strftime('%Y',Daily.ScheduleStartDate),LocationName,ProcedureCategory
) dv

ON b.Month = dv.Mnth AND b.Year = dv.Yr AND b.Location = dv.LocationName AND b.Modality = dv.ProcedureCategory

WHERE b.YEAR = "{year}"
GROUP BY b.MONTH,b.YEAR,b.Location,b.Modality''')
    df = pd.DataFrame(c.fetchall(), columns=['Month','Year','LocationName','Region','ProcedureCategory','ProjectDailyVolume','Days','Unit'])
    
    return df
#bt = basebudget()
#bt.dailybasebudget()
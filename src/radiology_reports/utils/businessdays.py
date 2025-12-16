# src/radiology_reports/utils/businessdays.py
import os
import csv
import datetime as dt
from datetime import date
from datetime import datetime
from calendar import monthrange
from matplotlib import pyplot as plt
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
import numpy as np
import daily
import pyodbc


cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))
#network_path = r'\\server4.rrc.center\public\dashboards\dailyreport'
#os.chdir(network_path)
os.chdir(app_path)
conn = pyodbc.connect('Driver={SQL Server};'
        'Server=PHISQL1.rrc.center;'
        'Database=RRC_Daily_Report;'
        'Trusted_Connection=yes;')
c = conn.cursor()



def years():
  try:
      output_file= os.path.join(app_path,r'output\businessdays-years.csv')
      f = open(output_file,"w+",newline='')
      
      daily1 = daily.Daily()
      
      #Year, Total
      total_year=daily1.YearTotals()
      
      dfMT = pd.DataFrame(columns=['Year','Total','BusinessDays','DailyAverage'])      

      for index,row in total_year.iterrows():
        businessdays = 0
        tempdf = daily1.databyyear(index)
        businessdays = getbusinessdays(tempdf)
        year_average = round(row['Unit']/ businessdays,1)
        temp = pd.DataFrame({'Year': [index],'Total':row['Unit'],
          'BusinessDays':[businessdays],'DailyAverage':[year_average]})
      
        dfMT = pd.concat([dfMT,temp],ignore_index=True)
        
      dfMT = dfMT.sort_values(by=['Year'],ascending = True)
      print(dfMT)
      dfMT.to_csv(f, sep=',', mode='a',line_terminator=None)
      print("file saved to ",output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def months(start,end):
  try:
    #get businessdays in array of days
    bdays = 0
    holidays = getholidays()
    
    bdc = np.busdaycalendar(holidays=holidays) #define custom holidays
    freq = CustomBusinessDay(calendar=bdc)
    #freq = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    
    bdays = pd.DataFrame(pd.bdate_range(start,end,freq=freq))
    bdays['Year'] = pd.to_datetime(bdays[0]).dt.year
    bdays['Month'] = pd.to_datetime(bdays[0]).dt.month
    bdays = pd.pivot_table(bdays,index=['Month','Year'],values='Year', columns=[], fill_value=0, aggfunc='count')

    bdays.rename(columns={0:'BusinessDays'},inplace=True)
    #print(bdays)
    return bdays

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)
    
def weeks():
  try:
      output_file= os.path.join(app_path,r'output\businessdays-weeks.csv')
      f = open(output_file,"w+",newline='')
      
      sql_query=('''SELECT ScheduleStartDate, datepart(year,ScheduleStartDate) as Year, 
      datepart(week,ScheduleStartDate) as Week,Sum(Unit) as Unit 
      FROM DAILY 
      WHERE ProcedureCategory != 'E&M CODES' AND ProcedureCategory != 'ENHANCED SRVC'
      GROUP BY ScheduleStartDate,datepart(year,ScheduleStartDate),datepart(week,ScheduleStartDate);''')

      data=pd.read_sql_query(sql_query,conn)
      #Format as dt
      data['ScheduleStartDate'] = pd.to_dt(data['ScheduleStartDate'])
      totalweekyear = pd.DataFrame(data.groupby(['Week','Year'])['Unit'].sum())
      
      dfMT = pd.DataFrame(columns=['Week','Year','Total','BusinessDays','DailyAverage'])      

      for index,row in totalweekyear.iterrows():
        businessdays = 0
        
        tempdf = data[data['Week'] == index[0]]
        tempdf = tempdf[tempdf['Year'] == index[1]]
    
        businessdays = getbusinessdays(tempdf)
        
        if(businessdays >0):
          week_average = round(row['Unit']/ businessdays,1)
        else: 
          week_average =0
          print("**Week",index[0],index[1],"has 0 businessdays**")

        tempdf['week_average'] = week_average
      
        temp = pd.DataFrame({'Week':[index[0]],'Year': [index[1]],'Total':[row['Unit']],
          'BusinessDays':[businessdays],'DailyAverage':[week_average]})
      
        dfMT = pd.concat([dfMT,temp],ignore_index=True)
                 
      dfMT = dfMT.sort_values(by=['Year','Week'],ascending = True)
      
      #display top 10 weeks
      print('Top 10 weeks \n', dfMT.sort_values(by=['Total'],ascending = False).head(10))
      
      dfMT.to_csv(f, sep=',', mode='a',line_terminator=None)
      print("file saved to ",output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def getholidays():
  try:
    sql_query=('''SELECT date FROM Holidays;''')

    data=pd.read_sql_query(sql_query,conn)
    holidays = np.array([dt.datetime.strptime(x,'%Y-%m-%d') for x in data['date']],dtype='datetime64[D]')
    
    #print(holidays)
    return holidays
    
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)
    
def gethalfdays(df):
    halfdays=[]
    df = df.dropna(subset=['Year'])    
    years = df['Year'].unique().astype(int)
    
    for iyear in years:
        #half days per Shawn\Alex\Dave email on 11/30/2020
        halfdays = np.append(halfdays,[
        dt.datetime(2017,11,24),dt.datetime(2018,11,23), #Thanksgiving
        dt.datetime(2019,11,29),dt.datetime(2020,11,27), #Thanksgiving
        dt.datetime(iyear,12,24), #Christmas
        dt.datetime(iyear,12,31)]) #New Years
    return halfdays

def getMTDbusinessdays(enddate):
    #get businessdays in array of days
    bdays = 0
    imonth = enddate.month
    iyear = enddate.year
    
    startdate = dt.datetime(iyear,imonth,1)
    enddate = enddate
    
    holidays = getholidays()
    bdc = np.busdaycalendar(holidays=holidays) #define custom holidays
    freq = CustomBusinessDay(calendar=bdc)
    bdays = pd.bdate_range(startdate,enddate,freq=freq)
    
    print('MTD ', enddate.strftime('%Y-%m-%d'), ' BusinessDays: ',len(bdays))
    return len(bdays)

def getYTDbusinessdays(enddate):
    #get businessdays in array of days
    bdays = 0
    iyear = enddate.year
    
    startdate = dt.datetime(iyear,1,1)
    enddate = enddate
    
    holidays = getholidays()
    bdc = np.busdaycalendar(holidays=holidays) #define custom holidays
    freq = CustomBusinessDay(calendar=bdc)
    bdays = pd.bdate_range(startdate,enddate,freq=freq)
    
    print('YTD ', enddate.strftime('%Y-%m-%d'), ' BusinessDays: ',len(bdays))
    #print(bdays)
    return bdays
    
def getbusinessdays(start,end):
    #get businessdays in array of days
    bdays = 0
    holidays = getholidays()
    bdc = np.busdaycalendar(holidays=holidays) #define custom holidays
    freq = CustomBusinessDay(calendar=bdc)
    bdays = pd.bdate_range(start,end,freq=freq)
    
    #print('BusinessDays: ',len(bdays))
    return len(bdays)





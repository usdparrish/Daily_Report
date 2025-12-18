import os
import csv
import datetime
from calendar import monthrange
from matplotlib import pyplot as plt
import pandas as pd
import argparse
import daily
import pyodbc

cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))
#network_path = r'\\server4.rrc.center\public\dashboards\dailyreport'
#os.chdir(network_path)
output_file= os.path.join(app_path,r'output\weektotals.csv')

now = datetime.datetime.now()
year = now.year

conn = pyodbc.connect('Driver={SQL Server};'
        'Server=PHISQL1.rrc.center;'
        'Database=RRC_Daily_Report;'
        'Trusted_Connectio=yes;')
c = conn.cursor()

def weeks():
  try:
    f = open(output_file,"w+",newline='')
    
    daily1 = daily.Daily()
    df = daily1.WeekTotals().reset_index(drop=True) #Week,Year,Volume
    
    #Export to csv
    df.to_csv(f, sep=',', mode='a',line_terminator=None)
    print('Exported to ', output_file)
      
    #Display top 10
    df = df.nlargest(10,'Volume').reset_index(drop=True)
    print("Top 10")
    print(df)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def weekdata():
  try:
    f = open(output_file,"w+",newline='')
    
    iyear = int(input("Year:"))
    iweek = input("Week 00-53:") 
    
    daily1 = daily.Daily()
    df = daily1.databyweekandyear(iweek,iyear)
    
    df.to_csv(f, sep=',', mode='a',line_terminator=None)
    print('Exported to ', output_file)
    
    print(df.head(5))
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekBudgetComparisonbyLocation():

  output_file= os.path.join(app_path,r'output\week_variance_by_location.csv')
  f = open(output_file,'w+',newline='')
  try:

    while True:
      iyear = int(input("Year:"))
      iweek = int(input("Week 00-53:"))
  
      if iweek >00 and iweek < 53 and iyear >2016 and iyear <= year:
        break
      else: 
        print ("Number is out of range")  
    
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.WeekLocationwithbudget(iweek,iyear).fillna(0)
      
      #Week Total
      dfTotal = WeekBudgetComparison(iweek,iyear)
      
      dfCombined = pd.DataFrame(pd.concat([df,dfTotal])).set_index('Location')
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)
      print(dfCombined)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekForecastComparisonbyLocation():
  output_file= os.path.join(app_path,r'output\week_forecast_variance_by_location.csv')
  f = open(output_file,'w+',newline='')
  try:
    iyear = int(input("Year:"))
    iweek = input("Week 00-53:")
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.WeekLocationwithforecast(iweek,iyear).fillna(0)
      
      #Week Total
      dfTotal = WeekForecastComparison(iweek,iyear)
      
      dfCombined = pd.DataFrame(pd.concat([df,dfTotal])).set_index('Location')
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)
      print(dfCombined)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekBaseBudgetComparisonbyLocation():
  output_file= os.path.join(app_path,r'output\week_basebudget_variance_by_location.csv')
  f = open(output_file,'w+',newline='')
  try:
    iyear = int(input("Year:"))
    iweek = input("Week 00-53:")
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.WeekLocationwithbasebudget(iweek,iyear).fillna(0)
      
      #Week Total
      dfTotal = WeekBaseBudgetComparison(iweek,iyear)
      
      dfCombined = pd.DataFrame(pd.concat([df,dfTotal])).set_index('Location')
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)
      print(dfCombined)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)
    
def WeekBudgetComparison(iweek,iyear):
  
  try:
      daily1 = daily.Daily()
      df = daily1.WeekTotalwithbudget(iweek,iyear)
      
      return df
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekForecastComparison(iweek,iyear):
  
  try:
      daily1 = daily.Daily()
      df = daily1.WeekTotalwithforecast(iweek,iyear)
      
      return df
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekBaseBudgetComparison(iweek,iyear):
  
  try:
      daily1 = daily.Daily()
      df = daily1.WeekTotalwithbasebudget(iweek,iyear)
      
      return df
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekwithBudget():
  output_file= os.path.join(app_path,r'output\week_variance.csv')
  f = open(output_file,'w+',newline='')
  try:
    iyear = int(input("Year:"))
    iweek = input("Week 00-53:")
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.Weekwithbudget(iweek,iyear).fillna(0)
      #df = df.sort_values(by='Vol_Var',ascending=True)
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print(df.head(5))
      print("file saved to ",output_file)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekwithForecast():
  output_file= os.path.join(app_path,r'output\week_forecast_variance.csv')
  f = open(output_file,'w+',newline='')
  try:
    iyear = int(input("Year:"))
    iweek = input("Week 00-53:")
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.Weekwithforecast(iweek,iyear).fillna(0)
      #df = df.sort_values(by='Vol_Var',ascending=True)
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print(df.head(5))
      print("file saved to ",output_file)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def WeekwithBaseBudget():
  output_file= os.path.join(app_path,r'output\week_variance.csv')
  f = open(output_file,'w+',newline='')
  try:
    iyear = int(input("Year:"))
    iweek = input("Week 00-53:")
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.Weekwithbasebudget(iweek,iyear).fillna(0)
      #df = df.sort_values(by='Vol_Var',ascending=True)
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print(df.head(5))
      print("file saved to ",output_file)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def getweekrank():
  
  try:
    #f = open(output_file,"w+",newline='')
    input_week = int(input("Week:")) 
    
    daily1 = daily.Daily()
    df = daily1.WeekTotals() #Week,Year,Volume
      
    #Set week rank
    df['rank'] = df['Volume'].rank(ascending=False)
    df = df[df['Week'] == input_week].reset_index(drop=True)
      
    #Export to csv file
    #df.to_csv(f, sep=',', mode='a',line_terminator=None)
    print(df)
    #print('Exported to ', output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def get10dayForecast():
  try:    
    output_file= os.path.join(app_path,r'output\10dayforecast.csv')
    f = open(output_file,"w+",newline='')
    
    #Exclude E&M Codes per Shawn and Dave on 03/23/2021
    #Added Region per Jennifer Ledet and Dave on 04/07/2022
    sql_query = (f'''SELECT s.dos,s.location,s.modality,
datepart(weekday,s.dos) as weekday, s.volume,s.inserted,d.sumunit,
datediff("d",s.inserted,s.dos) as daysout,
d.sumunit - s.volume as variance,
(s.volume *1.0/ d.sumunit) pct

FROM

(select dos,location,modality,sum(volume) volume, inserted from scheduled 
WHERE (datediff("d",getdate(),dos) <=60)
group by dos,location,modality,inserted) s

LEFT JOIN (

SELECT ScheduleStartDate as ddos, locationname, procedurecategory,sum(unit) sumunit
FROM DAILY 
WHERE (datediff("d",getdate(),ScheduleStartDate) <=60)
  AND ProcedureCategory != 'E&M CODES' AND ProcedureCategory != 'ENHANCED SRVC'
GROUP BY ScheduleStartDate,locationname,procedurecategory) d
on d.ddos = s.dos and d.locationname = s.location and d.procedurecategory = s.modality;''')
      
    df=pd.read_sql_query(sql_query,conn)
    df.to_csv(f, sep=',', mode='a',line_terminator=None)
    print('Exported to ', output_file)
    return df
  except Exception as e:
      template = "An exception of type {0} occurred. Arguments: \n{1!r}"
      message = template.format(type(e).__name__,e.args)
      print(message)

def locationandmodality():
  try:
    f = open(output_file,"w+",newline='')
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
      
    #Format as datetime
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate'])
    df['Year'] = pd.to_datetime(df['ScheduleStartDate']).dt.year
    df['Week'] = pd.to_datetime(df['ScheduleStartDate']).dt.week
      
    total_date = df.groupby(['LocationName','ProcedureCategory','Week','Year'])['Unit'].sum()
      
    #Export to csv file
    total_date.to_csv(f, sep=',', mode='a',line_terminator=None)
    print(total_date)
    print('Exported to ', output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)
    
def locationsvsbudget():
  try:
    f = open(output_file,"w+",newline='')
    input_week = int(input("Week:"))
    input_year = int(input("Year:"))
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
      
    #Format as datetime
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate'])
    df['Year'] = pd.to_datetime(df['ScheduleStartDate']).dt.year
    df['Week'] = pd.to_datetime(df['ScheduleStartDate']).dt.isocalendar().week
      
    df = df[df['Week'] == input_week]
    df = df[df['Year'] == input_year]
      
    total_date = df.groupby(['LocationName','ScheduleStartDate','Week','Year'])['Unit'].sum()
      
    #Export to csv file
    total_date.to_csv(f, sep=',', mode='a',line_terminator=None)
    print(total_date)
    print('Exported to ', output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def locationsbyday():
  try:
    f = open(output_file,"w+",newline='')
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
      
    #Format as datetime
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate'])
    df['Year'] = pd.to_datetime(df['ScheduleStartDate']).dt.year
    df['Week'] = pd.to_datetime(df['ScheduleStartDate']).dt.isocalendar().week
      
    total_date = df.groupby(['LocationName','ProcedureCategory','ScheduleStartDate','Week','Year'])['Unit'].sum()
     
    #Export to csv file
    total_date.to_csv(f, sep=',', mode='a',line_terminator=None)
    print(total_date)
    print('Exported to ', output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def modalities():
  try:
    f = open(output_file,"w+",newline='')
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
      
    #Format as datetime
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate'])
    df['Year'] = pd.to_datetime(df['ScheduleStartDate']).dt.year
    df['Week'] = pd.to_datetime(df['ScheduleStartDate']).dt.isocalendar().week
      
    total_date = df.groupby(['ProcedureCategory','Week','Year'])['Unit'].sum()
      
    #Export to csv file
    total_date.to_csv(f, sep=',', mode='a',line_terminator=None)
    #print(total_date)
    print('Exported to ', output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

import os
import csv
import datetime
from datetime import timedelta
import calendar
from calendar import monthrange
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import AutoMinorLocator
import pandas as pd
import numpy as np
import businessdays as bd
import budget
import daily
from jinja2 import Environment, FileSystemLoader
import pdfkit

today = datetime.date.today()
cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))


# src/radiology_reports/reporting/dailyreport.py
"""
Modern replacement for the old dailyreport.py
All SQL has been removed → uses only the data layer
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from radiology_reports.data.workload import get_data_by_date, get_outside_reads_by_date
from radiology_reports.services.budget import Budget
from radiology_reports.reporting.daily import DailyReport   # optional, if you want to reuse page logic


def dailystep1():
    """Exactly the same user experience as your original script"""
    date_str = input("Date (yyyy-mm-dd): ")
    target_date = datetime.strptime(date_str, "%Y-%m-%d")

    last_year_date = target_date - timedelta(days=364)
    two_years_date = target_date - timedelta(days=728)

    # ------------------------------------------------------------------
    # 1. Pull data using the new centralized layer
    # ------------------------------------------------------------------
    df_this = get_data_by_date(target_date)
    df_last = get_data_by_date(last_year_date)
    df_two = get_data_by_date(two_years_date)

    this_grouped = df_this.groupby(["Year", "LocationName", "ProcedureCategory", "Region"])["Unit"].sum()
    last_grouped = df_last.groupby(["Year", "LocationName", "ProcedureCategory", "Region"])["Unit"].sum()
    two_grouped = df_two.groupby(["Year", "LocationName", "ProcedureCategory", "Region"])["Unit"].sum()

    # ------------------------------------------------------------------
    # 2. Outside Reads
    # ------------------------------------------------------------------
    or_df = get_outside_reads_by_date(target_date)
    outside_reads = int(or_df["Unit"].iloc[0]) if not or_df.empty else 0

    # ------------------------------------------------------------------
    # 3. Budget (keep your existing Budget class – just move it to services/)
    # ------------------------------------------------------------------
    budget_obj = Budget(target_date.month, target_date.year)
    budget_df = budget_obj.getbudgetdf().groupby(
        ["Year", "LocationName", "ProcedureCategory", "Region"]
    )["Unit"].sum()

    # ------------------------------------------------------------------
    # 4. Write CSV exactly like you did before
    # ------------------------------------------------------------------
    output_file = Path(__file__).parent / "output" / "dailystep1.csv"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        f.write(f"Report Date,{target_date.strftime('%Y-%m-%d')}\n")
        f.write(f"Outside Reads,{outside_reads}\n\n")

        # Example – write this year data (you can copy the rest of your original loops)
        f.write("=== This Year ===\n")
        this_grouped.to_csv(f, header=True)

        f.write("\n=== Last Year ===\n")
        last_grouped.to_csv(f)

        f.write("\n=== Two Years Ago ===\n")
        two_grouped.to_csv(f)

        f.write("\n=== Budget ===\n")
        budget_df.to_csv(f)

    print(f"Output written to {output_file}")


# ----------------------------------------------------------------------
# Optional: CLI entry point (so you can run python -m radiology_reports.reporting.dailyreport)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # You can also accept date from command line later with argparse
    dailystep1()
    # Or generate the full PDF report:
    # report = DailyReport(datetime.today())
    report.generate_full_report()
   
def last8days():
  try:
      output_file= os.path.join(app_path,r'output\last8days.csv')
      f = open(output_file,'w+',newline='')
      daily1 = daily.Daily()
      df = daily1.getlastxdays(8)
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def dailybydayweek():
  output_file= os.path.join(app_path,r'output\daily_week.csv')
  f = open(output_file,'w+',newline='')
  week = input("Week 00-53:")
  iyear = int(input("Year:"))
  try:
      daily1 = daily.Daily()
      df = daily1.databyweek(week,iyear)
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)
       
def dailybydaydaterange():
  
  try:
    output_file= os.path.join(app_path,r'output\dailybyday.csv')
    f = open(output_file,'w+',newline='')
    print("Date Format yyyyy-mm-dd")
    istart = input("Start Date:")
    iend = input("End Date:")
    daily1 = daily.Daily()
    df = daily1.databydaterange(istart, iend)
    
    print(df.head(10))
    df.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print("file saved to ",output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def dailybydaymonthyear():
  try:
    output_file= os.path.join(app_path,r'output\dailybyday.csv')
    f = open(output_file,'w+',newline='')
    imonth = int(input("Month:"))
    iyear = int(input("Year:"))
    
    if imonth >0 and imonth < 13 and iyear >2016:
      daily1 = daily.Daily()
      df = daily1.databymonthandyear(imonth,iyear).groupby(['Year','ScheduleStartDate','LocationName','ProcedureCategory'])['Unit'].sum()
      
      #Export to csv
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      
      print('Export to csv: ',output_file)
      #dfCombinedPivot = dfCombined.pivot_table(index=['Year','ProcedureCategory'],values='Unit', columns='LocationName', fill_value=0, aggfunc=np.sum)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def dailybydayyearmodality():
  global input_day
  global iyear
  
  try:
    iyear = int(input("Year:"))
    
    if iyear >2016:
      df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
      df = addcolumns(df)

      #New dataframe for this year
      thisyeardf = df.copy(deep=False)
      thisyeardf = thisyeardf[thisyeardf['Year'] == iyear]

      #Group by Year, Location, ProcedureCategory   
      thisyeardf = thisyeardf.groupby(['Year','ScheduleStartDate','ProcedureCategory','SameDayLastYear'])['Unit'].sum()
      
      print(thisyeardf)
      thisyeardf.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)
      #dfCombinedPivot = dfCombined.pivot_table(index=['Year','ProcedureCategory'],values='Unit', columns='LocationName', fill_value=0, aggfunc=np.sum)

    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def dailybydayyearlocation():
   
  try:
    iyear = int(input("Year:"))
    
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.databyyear(iyear)

      #Group by Year, Location  
      tempdf = df.groupby(['ScheduleStartDate','LocationName'])['Unit'].sum()
      
      tempdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)
      print(tempdf)

    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def dailybydayyearmonthlocationandmodality():
  global iyear
  
  try:
    iyear = int(input("Year:"))
    
    if iyear >2016:
      df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
      df = addcolumns(df)
      df['Month'] = pd.to_datetime(df['ScheduleStartDate']).dt.month

      #New dataframe for this year
      thisyeardf = df.copy(deep=False)
      thisyeardf = thisyeardf[thisyeardf['Year'] == iyear]

      #Group by Year, Location  
      thisyeardf = thisyeardf.groupby(['Year','Month','ScheduleStartDate','LocationName','ProcedureCategory','SameDayLastYear'])['Unit'].sum()
      
      print(thisyeardf)
      thisyeardf.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("file saved to ",output_file)

    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def AllSaturdays(): 
  try:
    output_file= os.path.join(app_path,r'output\dailybyday.csv')
    f = open(output_file,'w+',newline='')
    daily1 = daily.Daily()
    
    #Filter only Saturdays
    df = daily1.databyweekday(7)

    #Pivot by ScheduleStartDate and Location
    satdf = pd.DataFrame(df.groupby(['ScheduleStartDate','Year','LocationName','ProcedureCategory'])['Unit'].sum())
    
    #Export to csv
    satdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print('Export to csv: ',output_file)
    
    #Group by Year, Location, ProcedureCategory   
    satdf =  pd.DataFrame(satdf.groupby(['ScheduleStartDate'])['Unit'].sum())
    #satdf = satdf.groupby(['Year','ScheduleStartDate','ProcedureCategory','Weekday'])['Unit'].sum()

    #Set rank
    satdf['rank'] = satdf['Unit'].rank(ascending=False)
    print( '\n**Last 5 Saturdays with rank**\n',satdf.sort_index(ascending=False).head(5) )

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def SaturdaysbyLocation(): 
  try:
    output_file= os.path.join(app_path,r'output\dailybyday.csv')
    f = open(output_file,'w+',newline='')
    print("Date Format yyyyy-mm-dd")
    istart = input("Start Date:")
    iend = input("End Date:")
    daily1 = daily.Daily()
    df = daily1.databydaterange(istart, iend)
    
    #New dataframe for this year
    df['Weekday'] = pd.to_datetime(df['ScheduleStartDate']).dt.weekday #Monday=0, Sunday=6
      
    #Filter only Saturdays
    satdf = df[df['Weekday'] == 5]
    #Pivot by ScheduleStartDate and Location
    dfPivot = satdf.pivot_table(index=['ScheduleStartDate'],values='Unit', columns='LocationName', fill_value=0, aggfunc=np.sum)
    
    #Export to csv
    dfPivot.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print('file save to: ',output_file)
    print(dfPivot.head(5))

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def LocationPreviousYearVariance(): 
  try:
    output_file= os.path.join(app_path,r'output\prev_year_variance.csv')
    f = open(output_file,'w+',newline='')
    print("Date Format yyyyy-mm-dd")

    idate = input("Date:")
    daily1 = daily.Daily() 
    data = daily1.datelocationpreviousyearvariance(idate)     
    dataTotal = daily1.datelocationpreviousyeartotalsvariance(idate)
    
    df = pd.concat([data,dataTotal])
    #Export to csv
    df.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print('file save to: ',output_file)
    print(df)
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def dailybydaydaynum(): 
  try:
    output_file= os.path.join(app_path,r'output\dailybyday.csv')
    f = open(output_file,'w+',newline='')
    idaynum = int(input("DayNum \n(Sunday=0):")) 
    
    if idaynum >=0 and idaynum <=7:
      daily1 = daily.Daily()
      df = daily1.databyweekday(idaynum)

      #Pivot by ScheduleStartDate and Location
      df = pd.DataFrame(df.groupby(['ScheduleStartDate','Year','LocationName','ProcedureCategory'])['Unit'].sum())
      #df = df.pivot_table(index=['LocationName','ProcedureCategory'],values='Unit', columns=['ScheduleStartDate'], fill_value=0, aggfunc=np.sum)
    
      #Export to csv
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print('Export to csv: ',output_file)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def alldaterange():
  global input_startday
  global input_endday
  
  try:
    output_file= os.path.join(app_path,r'output\alldata.csv')
    f = open(output_file,'w+',newline='')
    print("Date Format yyyyy-mm-dd")
    istart = input("Start Date:")
    iend = input("End Date:")
    daily1 = daily.Daily()
    df = daily1.alldatadaterange(istart, iend)
    
    #print(df.head(10))
    df.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print("file saved to ",output_file)

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)
 
def modalitytop5():
    output_file= os.path.join(app_path,r'output\top5.txt')
    f = open(output_file,'w+',newline='')
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate']).dt.date
    total_procedures = df.groupby(['ProcedureCategory','ScheduleStartDate'])['Unit'].sum()#.nlargest(10)
    #print(total_procedures)
    
    f.write('Modality Top 5\nAs of ')
    f.write(today.strftime("%B %d, %Y"))
    f.write('\n')
    
    #Loop each ProcedureCategory and get top 10
    categories = df['ProcedureCategory'].unique()
    for x in categories:
        f.write('-------------------------\n**')
        f.write(x)
        f.write('**\n')
        newquery = df[df['ProcedureCategory'] == x]
        total_date_category = newquery.groupby(['ScheduleStartDate'])['Unit'].sum().nlargest(5)
        total_date_category.to_csv(f, sep='\t', mode='a', encoding='utf-8', header=False)
    #total_procedures.to_csv(f, sep=',', mode='a',line_terminator=None)
    print('output_file: ',output_file)
    
def locationmodalitytop5():
    output_file= os.path.join(app_path,r'output\top5.txt')
    f = open(output_file,'w+',newline='')
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate']).dt.date
    total_procedures = df.groupby(['LocationName','ProcedureCategory','ScheduleStartDate'])['Unit'].sum()#.nlargest(10)
    #print(total_procedures)
    
    f.write('Location\Modality Top 5\nAs of ')
    f.write(today.strftime("%B %d, %Y"))
    f.write('\n')
    
    #Loop each ProcedureCategory and get top 10
    locations = df['LocationName'].unique()
    
    for l in locations:
        f.write('-------------------------\n')
        df2 = df[df['LocationName'] == l]
        categories = df2['ProcedureCategory'].unique()
        for x in categories:
            f.write('**')
            f.write(l)
            f.write(' (')
            f.write(x)
            f.write(')**\n')
            newquery = df2[df2['ProcedureCategory'] == x]
            total_date_category = newquery.groupby(['ScheduleStartDate'])['Unit'].sum().nlargest(5)
            total_date_category.to_csv(f, sep='\t', mode='a', encoding='utf-8', header=False)
            f.write('\n')
    #total_procedures.to_csv(f, sep=',', mode='a',line_terminator=None)
    print('output_file: ',output_file)

def modalitylocationtop():
    output_file= os.path.join(app_path,r'output\top1.txt')
    f = open(output_file,'w+',newline='')
    df = pd.DataFrame(c.fetchall(), columns=['ScheduleStartDate','LocationName','ProcedureCategory','Unit'])
    df['ScheduleStartDate'] = pd.to_datetime(df['ScheduleStartDate']).dt.date
    total_procedures = df.groupby(['LocationName','ProcedureCategory','ScheduleStartDate'])['Unit'].sum()#.nlargest(10)
    #print(total_procedures)

    f.write('Modality\Location Top Day\nAs of ')
    f.write(today.strftime("%B %d, %Y"))
    f.write('\n')
    
    #Loop each ProcedureCategory and get top 10
    
    categories = df['ProcedureCategory'].unique()
    thislist = []
    for t in categories:
        f.write('-------------------------\n')
        f.write('**')
        f.write(t)
        f.write('**\n')
        df2 = df[df['ProcedureCategory'] == t]
        locations = df2['LocationName'].unique()
        thislist.append(t)
        for x in locations: 
            #f.write(x)
            #f.write(',')            
            newquery = df2[df2['LocationName'] == x]
            dfT = newquery.groupby(['ScheduleStartDate'])['Unit'].sum().nlargest(1).reset_index()
            #z = dfT['ScheduleStartDate'].values.tolist()
            thislist =[x]
            #z=[d.strftime('%Y-%m-%d') for d in z]
            #thislist.append(z)
            thislist.append(dfT['ScheduleStartDate'][0].strftime('%Y-%m-%d'))
            thislist.append('(' + str(dfT['Unit'][0]) + ')')
            #dfT.to_csv(f, sep=',', mode='a', encoding='utf-8', header=False)
            f.write(' -> '.join([str(item) for item in thislist]))
            f.write('\n')
    print(thislist)        
    #total_procedures.to_csv(f, sep=',', mode='a',line_terminator=None)
    print('output_file: ',output_file)




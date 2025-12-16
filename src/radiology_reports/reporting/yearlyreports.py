import os
import sys
import csv
import datetime
from datetime import datetime as dt
from datetime import timedelta
import calendar
import pandas as pd
import numpy as np
import businessdays as bd
import budget
import daily


#os.chdir('')
cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))
#network_path = r'\\server4.rrc.center\public\dashboards\dailyreport'
#os.chdir(network_path)

def getYTDPrevYearDate(ddate):
    try:
      imonth = ddate.month
      iyear = ddate.year
        
      lastyear = ddate - timedelta(days=364)
      print('Last year date: ', lastyear,' (364 days ago)')
        
      if(lastyear.month == imonth +1):
        lastday = calendar.monthrange(lastyear.year,imonth)[1]
        lastyear = datetime.datetime(lastyear.year,imonth,lastday)
        print('Using ',lastyear, ' instead')
      return lastyear
    except Exception as e:
      template = "An exception of type {0} occurred. Arguments: \n{1!r}"
      message = template.format(type(e).__name__,e.args)
      print(message)

def getYTD2YearsDate(ddate):
    try:
      imonth = ddate.month
      iyear = ddate.year
        
      lastyear = ddate - timedelta(days=728)
      print('Two year date: ', lastyear,' (728 days ago)')
        
      if(lastyear.month == imonth +1):
        lastday = calendar.monthrange(lastyear.year,imonth)[1]
        lastyear = datetime.datetime(lastyear.year,imonth,lastday)
        print('Using ',lastyear, ' instead')
      return lastyear
    except Exception as e:
      template = "An exception of type {0} occurred. Arguments: \n{1!r}"
      message = template.format(type(e).__name__,e.args)
      print(message)   

def YTDVsPrevYear():
  print("Date Format yyyyy-mm-dd")
  strdate = input("Date:")
  
  try:
    businessdays = 0
    
    ddate = dt.strptime(strdate,'%Y-%m-%d')
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016:
      daily1 = daily.Daily() 
             
      lastyear = getYTDPrevYearDate(ddate)
         
      df = daily1.datamonthtodate(ddate) #dataframe
      lastyeardf = daily1.datamonthtodate(lastyear)
                  
      df = pd.concat([df,lastyeardf]) #Combine
      tempdf = df.groupby(['Year'])['Unit'].sum().reset_index()
      locations = df['LocationName'].unique()
      print(locations)
      
      bdlist=[] #list of businessdays
      
      #last year businessdays MTD
      businessdays = bd.getYTDbusinessdays(lastyear) 
      bdlist.append(businessdays)

      #this year businessdays MTD
      businessdays = bd.getYTDbusinessdays(ddate) 
      bdlist.append(businessdays)
        
      tempdf['days'] = bdlist 
      tempdf['average'] = round((tempdf.iloc[:,1] / tempdf.iloc[:,2]),1)      
      print(tempdf)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def YTDSameStoreVsPrevYear():
  print("Date Format yyyyy-mm-dd")
  sdate = input("Start Date:")
  edate = input("End Date:")
  
  output_file= os.path.join(app_path,r'output\ytd_samestore.csv')
  f = open(output_file,'w+',newline='')
  
  a = pd.date_range(start=sdate, end=edate)
 
  daily1 = daily.Daily()
  appended_data=[]
  # iterate over range of dates
  for i in a:  
    df = daily1.dateSameStoreVsPrevYear(i.date())
    appended_data.append(df)
    
  appended_data = pd.concat(appended_data)
  #appended_data.reset_index(drop=True, inplace=True)
  
  locations = appended_data['LocationName'].unique()
  print(locations)
  
  # Totals
  df_Totals = appended_data.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
  
  #appended_data['Vol_Var'] = appended_data.iloc[:,1] - appended_data.iloc[:,0]
  #appended_data['Pct_Var'] = round(((appended_data.iloc[:,1] - appended_data.iloc[:,0])/appended_data.iloc[:,0]),3) *100
  
  print(df_Totals)
  #print(appended_data.sum(axis=0,skipna=True))
  
  print("file saved to ",output_file) 
  appended_data.to_csv(f,sep=',',mode='w+',line_terminator=None)

def yearstep1():
  try:
    print("Date Format yyyyy-mm-dd")
    strdate = input("Date:")
    ddate = dt.strptime(strdate,'%Y-%m-%d')
  
    now = datetime.datetime.now()
    output_file= os.path.join(app_path,r'output\yearstep1.csv')
    f = open(output_file,'w+',newline='')

    global imonth
    global iyear
    
    businessdays = 0
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016:

      lastyear = getYTDPrevYearDate(ddate)
      d2Years = getYTD2YearsDate(ddate)
      
      daily1 = daily.Daily()
      
      #dataframe for this year
      thisyeardf = daily1.datayeartodate(enddate)
      
      #dataframe for this year #Group by Year, Location, ProcedureCategory  
      thisyeardf = thisyeardf.groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()

      #dataframe for last year (same day of week)
      lastyeardf = daily1.datayeartodate(lastyear).groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()

      #dataframe for 2 years ago (same day of week)
      twoyearsdf = daily1.datayeartodate(d2Years).groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()
      
      budgetdf = getYTDBudgetwithBusinessdays(enddate)   
      budgetdf = budgetdf.groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()

      if twoyearsdf.empty == True:
        print('twoyeardf is empty')
        dfCombined = pd.concat([thisyeardf,budgetdf]) #Combine budget to Combined1
      else: 
        dfCombined = pd.concat([thisyeardf,twoyearsdf,budgetdf]) #Combine to Combined1  
      
      if lastyeardf.empty == True:
        print('lastyeardf is empty')
      else:
        dfCombined = pd.DataFrame(pd.concat([lastyeardf,dfCombined])) #Combine budget to Combined1
      
      #Save to csv
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("File saved to ",output_file)
      
      df_Final = dfCombined.pivot_table(index=['Region','LocationName'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      df_Region = dfCombined.pivot_table(index=['Region'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      df_Totals = dfCombined.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      
      cols1 = df_Final.columns.tolist()
      cols2 = df_Totals.columns.tolist()
      
      #print(df_Final.head(10))
      #sys.exit()      

      #Dataframe with difference compared to previous year
      print('Difference = (ThisYear - Budget) / Budget')
      if lastyeardf.empty != True and budgetdf.empty != True:
          df_Final['Vol_Var'] = round((df_Final.iloc[:,2] - df_Final.iloc[:,3]),3)
          df_Final['Pct_Var'] = round(((df_Final.iloc[:,2] - df_Final.iloc[:,3])/df_Final.iloc[:,3]),3) * 100
          
          df_Region['Vol_Var'] = round((df_Region.iloc[:,2] - df_Region.iloc[:,3]),3)
          df_Region['Pct_Var'] = round(((df_Region.iloc[:,2] - df_Region.iloc[:,3])/df_Region.iloc[:,3]),3) * 100
          
          df_Totals['Vol_Var'] = round((df_Totals.iloc[:,2] - df_Totals.iloc[:,3]),3)
          df_Totals['Pct_Var'] = round(((df_Totals.iloc[:,2] - df_Totals.iloc[:,3])/df_Totals.iloc[:,3]),3) * 100
      else:    
          print('Last Year and Budget Empty')
          
      df_Totals['Region'] = ''
      df_Totals['LocationName'] = 'TOTAL'
      
      df_Totals[cols2] = df_Totals[cols2].astype(int).applymap(lambda x:f'{x:,}')
      
      df5 = df_Totals.set_index(['Region','LocationName'])
      
      df_Final[cols1] = df_Final[cols1].astype(int).applymap(lambda x:f'{x:,}')
            
      df5 = pd.concat([df_Final,df5]).fillna('-')
       
      df5['Vol_Var'] = df5['Vol_Var'].apply(lambda x:'{:,}'.format(x))
        
      print('\n',df5.fillna('-'))
      #print('\n', df_Region.fillna(0))
      #print('Totals:\n',df_Totals.fillna(0))
      return dfCombined

    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def yearbymonth():
  try:
    iyear = int(input("Year:"))
    if iyear >2016:
      daily1 = daily.Daily()
      df = daily1.databyyear(iyear)
      sum_vol = df['Unit'].sum()
      df = df.pivot_table(index=['Month'],values='Unit', fill_value=0, aggfunc=np.sum).sort_values(by='Month')
      
      print(df)
      print("Total:",sum_vol)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)    
    
def YTDbyMonthwithBudget():
  
  try:
    output_file= os.path.join(app_path,r'output\ytd_variance.csv')
    f = open(output_file,'w+',newline='')
    print("Date Format yyyyy-mm-dd")
    strdate = input("Date:")
    ddate = dt.strptime(strdate,'%Y-%m-%d')
    now = datetime.datetime.now()

    businessdays = 0
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016: 
      daily1 = daily.Daily()
      
      #dataframe for this year
      thisyeardf = daily1.datayeartodate(enddate).groupby(['Month','Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()       
      budgetdf = getYTDBudgetwithBusinessdays(enddate).groupby(['Month','Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()
      
      if thisyeardf.empty == True:
        print('twoyeardf is empty')
      else: 
        dfCombined = pd.DataFrame(pd.concat([thisyeardf,budgetdf])) #Combine budget to Combined1
     
      #Save to csv
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("File saved to ",output_file)
      
      df_Final = dfCombined.pivot_table(index=['Month'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      #df_Region = dfCombined.pivot_table(index=['Region'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      df_Totals = dfCombined.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      
      cols1 = df_Final.columns.tolist()
      cols2 = df_Totals.columns.tolist()
      
      #print(df_Final.head(10))
      #sys.exit()      

      #Dataframe with difference compared to previous year
      print('Difference = (ThisYear - Budget) / Budget')
      if thisyeardf.empty != True and budgetdf.empty != True:
          df_Final['Vol_Var'] = round((df_Final.iloc[:,0] - df_Final.iloc[:,1]),3)
          df_Final['Pct_Var'] = round(((df_Final.iloc[:,0] - df_Final.iloc[:,1])/df_Final.iloc[:,1]),3) * 100
          
          #df_Region['Vol_Var'] = round((df_Region.iloc[:,2] - df_Region.iloc[:,3]),3)
          #df_Region['Pct_Var'] = round(((df_Region.iloc[:,2] - df_Region.iloc[:,3])/df_Region.iloc[:,3]),3) * 100
          
          df_Totals['Vol_Var'] = round((df_Totals.iloc[:,0] - df_Totals.iloc[:,1]),3)
          df_Totals['Pct_Var'] = round(((df_Totals.iloc[:,0] - df_Totals.iloc[:,1])/df_Totals.iloc[:,1]),3) * 100
      else:    
          print('This Year and Budget Empty')
          
      df_Totals['Month'] = 'TOTAL'
      
      df_Totals[cols2] = df_Totals[cols2].astype(int).applymap(lambda x:f'{x:,}')
      
      df5 = df_Totals.set_index(['Month'])
      
      df_Final[cols1] = df_Final[cols1].astype(int).applymap(lambda x:f'{x:,}')
            
      df5 = pd.concat([df_Final,df5]).fillna('-')
       
      df5['Vol_Var'] = df5['Vol_Var'].apply(lambda x:'{:,}'.format(x))
        
      print('\n',df5.fillna('-'))
      #print('\n', df_Region.fillna(0))
      #print('Totals:\n',df_Totals.fillna(0))
      return dfCombined
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def YTDbyMonthbyLocationwithBudget():
  try:
    print("Date Format yyyyy-mm-dd")
    strdate = input("Date:")
    ddate = dt.strptime(strdate,'%Y-%m-%d')
  
    now = datetime.datetime.now()
    output_file= os.path.join(app_path,r'output\ytd_variance.csv')
    f = open(output_file,'w+',newline='')
    
    businessdays = 0
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016:

      daily1 = daily.Daily()
      df = daily1.datayeartodate(enddate)
      df = df[df['Month'] <= imonth] 
      df = df.groupby(['Month','Year','LocationName'])['Unit'].sum()
      budgetdf = getYTDBudgetwithBusinessdays(enddate).groupby(['Month','Year','LocationName'])['Unit'].sum()   

      dfCombined = pd.DataFrame(pd.concat([df,budgetdf])) #Combine budget to Combined1
      #df['DailyAvg'] = round((df['Unit'] / df['BusinessDays']),1)   

      #Save to csv
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("File saved to ",output_file)
      
      df_Final = dfCombined.pivot_table(index=['Month','LocationName'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      #df_Region = dfCombined.pivot_table(index=['Region'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      df_Totals = dfCombined.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      
      cols1 = df_Final.columns.tolist()
      cols2 = df_Totals.columns.tolist()
      
      #print(df_Final.head(10))
      #sys.exit()      

      #Dataframe with difference compared to previous year
      print('Difference = (ThisYear - Budget) / Budget')
      if df.empty != True and budgetdf.empty != True:
          df_Final['Vol_Var'] = round((df_Final.iloc[:,0] - df_Final.iloc[:,1]),3)
          df_Final['Pct_Var'] = round(((df_Final.iloc[:,0] - df_Final.iloc[:,1])/df_Final.iloc[:,1]),3) * 100
          
          #df_Region['Vol_Var'] = round((df_Region.iloc[:,2] - df_Region.iloc[:,3]),3)
          #df_Region['Pct_Var'] = round(((df_Region.iloc[:,2] - df_Region.iloc[:,3])/df_Region.iloc[:,3]),3) * 100
          
          df_Totals['Vol_Var'] = round((df_Totals.iloc[:,0] - df_Totals.iloc[:,1]),3)
          df_Totals['Pct_Var'] = round(((df_Totals.iloc[:,0] - df_Totals.iloc[:,1])/df_Totals.iloc[:,1]),3) * 100
      else:    
          print('This Year and Budget Empty')
          
      df_Totals['Month'] = ''
      df_Totals['LocationName'] = 'TOTAL'
      
      df_Totals[cols2] = df_Totals[cols2].astype(int).applymap(lambda x:f'{x:,}')
      
      df5 = df_Totals.set_index(['Month','LocationName'])
      
      df_Final[cols1] = df_Final[cols1].astype(int).applymap(lambda x:f'{x:,}')
            
      df5 = pd.concat([df_Final,df5]).fillna('-')
       
      df5['Vol_Var'] = df5['Vol_Var'].apply(lambda x:'{:,}'.format(x))
        
      print('\n',df5.head(10).fillna('-'))

    else:
      print ("Number is out of range") 

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def getYTDBudgetwithBusinessdays(ddate):
  try:
    output_file= os.path.join(app_path,r'output\ytd_budget.csv')
    f = open(output_file,'w+',newline='')

    businessdays = 0
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016:
      
      #get this year\month businessdays
      businessdays = bd.getYTDbusinessdays(enddate)
      bdaydf = pd.DataFrame(businessdays)
      bdaydf['Month'] = pd.to_datetime(bdaydf[0]).dt.month
      bdaydf = pd.DataFrame(bdaydf.groupby(['Month']).count()).reset_index().rename(columns={0:'BusinessDays'})      

      #budget
      budget1 = budget.Budget(0,iyear)
      
      #Empty DataFrame; #comment out if budget is enabled
      #budgetdf = pd.DataFrame(columns=['LocationName','ProcedureCategory','Year','Month','Unit'])
      
      budgetdf = pd.DataFrame(budget1.getYearBudgetProjDaily(iyear).groupby(['Month','Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()).reset_index()#uncomment to add budget
      
      budgetdf = budgetdf[budgetdf['Month'] <= imonth]      
      budgetdf = pd.merge(budgetdf,bdaydf,on='Month',how='inner')
      budgetdf['BudgetVol'] = round((budgetdf['Unit'] * budgetdf['BusinessDays']),0) 
      budgetdf = budgetdf.drop(columns=['Unit']).rename(columns={'BudgetVol':'Unit'})
      #print(budgetdf.head(10))
      #sys.exit()      
      #budgetdf = budgetdf.groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()
       
      budgetdf.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("File saved to ",output_file)
      return(budgetdf)
    else:
      print ("Number is out of range")
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def YTDDailyAvgbyLocationbyModality():
  try:
    print("Date Format yyyyy-mm-dd")
    strdate = input("Date:")
    ddate = dt.strptime(strdate,'%Y-%m-%d')
  
    now = datetime.datetime.now()
    output_file= os.path.join(app_path,r'output\ytd_dailyavg.csv')
    f = open(output_file,'w+',newline='')
    
    businessdays = 0
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016:

      daily1 = daily.Daily()
      df = daily1.datayeartodate(enddate)
      df = df[df['Month'] <= imonth] 
      df = pd.DataFrame(df.groupby(['Month','LocationName','ProcedureCategory'])['Unit'].sum()).reset_index()
                      
      #get this year\month businessdays
      businessdays = bd.getYTDbusinessdays(enddate)
      bdaydf = pd.DataFrame(businessdays)
      bdaydf['Month'] = pd.to_datetime(bdaydf[0]).dt.month
      bdaydf = pd.DataFrame(bdaydf.groupby(['Month']).count()).reset_index().rename(columns={0:'BusinessDays'})      

      df = pd.merge(df,bdaydf,on='Month',how='inner')
      df['DailyAvg'] = round((df['Unit'] / df['BusinessDays']),1) 
      
      print(df.head(10)) 
      #df = df.sort_values(by='Vol_Var',ascending=True)
      df.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("File saved to ",output_file)  

    else:
      print ("Number is out of range")      

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)

def YTDDailyAvgbyLocationwithBudget():
  try:
    print("Date Format yyyyy-mm-dd")
    strdate = input("Date:")
    ddate = dt.strptime(strdate,'%Y-%m-%d')
  
    now = datetime.datetime.now()
    output_file= os.path.join(app_path,r'output\ytd_dailyavg.csv')
    f = open(output_file,'w+',newline='')
    
    businessdays = 0
    imonth = ddate.month
    iyear = ddate.year
    startdate = datetime.datetime(iyear,imonth,1)
    enddate = ddate
    
    if imonth >0 and imonth < 13 and iyear >2016:

      daily1 = daily.Daily()
      df = daily1.datayeartodate(enddate)
      df = df[df['Month'] <= imonth] 
      df = df.groupby(['Month','Year','LocationName'])['Unit'].sum()
      budgetdf = getYTDBudgetwithBusinessdays(enddate).groupby(['Month','Year','LocationName','BusinessDays'])['Unit'].sum()   

      dfCombined =  pd.merge(budgetdf,df,on=['Month','LocationName'],how='inner')
      #dfCombined = pd.DataFrame(pd.concat([df,budgetdf])) #Combine budget to Combined1
      #df['DailyAvg'] = round((df['Unit'] / df['BusinessDays']),1)   

      print(dfCombined.head(10))
      sys.exit()

      #Save to csv
      dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
      print("File saved to ",output_file)
      
      df_Final = dfCombined.pivot_table(index=['Month','LocationName'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      #df_Region = dfCombined.pivot_table(index=['Region'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      df_Totals = dfCombined.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
      
      cols1 = df_Final.columns.tolist()
      cols2 = df_Totals.columns.tolist()
      
      #print(df_Final.head(10))
      #sys.exit()      

      #Dataframe with difference compared to previous year
      print('Difference = (ThisYear - Budget) / Budget')
      if df.empty != True and budgetdf.empty != True:
          df_Final['Vol_Var'] = round((df_Final.iloc[:,0] - df_Final.iloc[:,1]),3)
          df_Final['Pct_Var'] = round(((df_Final.iloc[:,0] - df_Final.iloc[:,1])/df_Final.iloc[:,1]),3) * 100
          
          #df_Region['Vol_Var'] = round((df_Region.iloc[:,2] - df_Region.iloc[:,3]),3)
          #df_Region['Pct_Var'] = round(((df_Region.iloc[:,2] - df_Region.iloc[:,3])/df_Region.iloc[:,3]),3) * 100
          
          df_Totals['Vol_Var'] = round((df_Totals.iloc[:,0] - df_Totals.iloc[:,1]),3)
          df_Totals['Pct_Var'] = round(((df_Totals.iloc[:,0] - df_Totals.iloc[:,1])/df_Totals.iloc[:,1]),3) * 100
      else:    
          print('This Year and Budget Empty')
          
      df_Totals['Month'] = ''
      df_Totals['LocationName'] = 'TOTAL'
      
      df_Totals[cols2] = df_Totals[cols2].astype(int).applymap(lambda x:f'{x:,}')
      
      df5 = df_Totals.set_index(['Month','LocationName'])
      
      df_Final[cols1] = df_Final[cols1].astype(int).applymap(lambda x:f'{x:,}')
            
      df5 = pd.concat([df_Final,df5]).fillna('-')
       
      df5['Vol_Var'] = df5['Vol_Var'].apply(lambda x:'{:,}'.format(x))
        
      print('\n',df5.head(10).fillna('-'))

    else:
      print ("Number is out of range") 

  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)



import os
import csv
import datetime
from datetime import datetime, date
from datetime import timedelta
import calendar
from calendar import monthrange
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import sqlite3
import businessdays as bd
import budget
import basebudget
import forecast
import daily
import pyodbc
from typing import Tuple, List, Union

cur_path = os.getcwd()
app_path = os.path.dirname(os.path.abspath(__file__))
#network_path = r'\\server4.rrc.center\public\dashboards\dailyreport'
#os.chdir(network_path)

conn = pyodbc.connect('Driver={SQL Server};'
        'Server=PHISQL1.rrc.center;'
        'Database=RRC_Daily_Report;'
        'Trusted_Connectio=yes;')
c = conn.cursor()

output_file= os.path.join(app_path,r'output\quartertotals.csv')
#print(output_file)
f = open(output_file,"w+",newline='')

# ----------------------------------------------------------------------
def quarter_bounds(year: int, quarter: str) -> Tuple[date, date]:
    """
    Return (first_day, last_day) of the calendar quarter.
    Handles leap years automatically.
    """
    q = quarter.upper().strip()
    if q not in {"Q1", "Q2", "Q3", "Q4"}:
        raise ValueError(f'Invalid quarter "{quarter}". Use Q1‑Q4.')

    # map quarter → first month of that quarter
    start_month = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[q]
    end_month   = start_month + 2

    start_dt = date(year, start_month, 1)
    # days_in_month gives the correct last day (accounts for Feb‑29)
    last_day = calendar.monthrange(year, end_month)[1]
    end_dt   = date(year, end_month, last_day)

    return start_dt, end_dt


# ----------------------------------------------------------------------
def quarters() -> None:
    """
    Build `businessdays-quarters.csv` containing, for every quarter‑year:
        • Quarter (Q1‑Q4)
        • Year
        • Total units (from Daily.QuarterYearTotals)
        • BusinessDays (calculated from start‑/end‑dates)
        • DailyAverage = Total / BusinessDays
        • StartDate, EndDate (calendar bounds of the quarter)

    The CSV is written to `<app_path>/output/businessdays-quarters.csv`.
    """
    try:
        # --------------------------------------------------------------
        # 1️⃣ Prepare output location
        output_file = os.path.join(app_path, 'output', 'businessdays-quarters.csv')
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # --------------------------------------------------------------
        # 2️⃣ Pull the quarter‑year totals from your existing Daily helper
        now = datetime.now()
        daily1 = daily.Daily()                       # <- make sure `daily` is imported
        total_quarter = daily1.QuarterYearTotals()   # DataFrame indexed by (Quarter, Year)

        # Columns we will finally write
        cols = ['Quarter', 'Year', 'Total', 'BusinessDays',
                'DailyAverage', 'StartDate', 'EndDate']
        df_report = pd.DataFrame(columns=cols)

        # --------------------------------------------------------------
        # 3️⃣ Iterate over each quarter‑year pair
        for (quarter_label, year_val), row in total_quarter.iterrows():
            # a) Calendar bounds for this quarter
            start_dt, end_dt = quarter_bounds(int(year_val), quarter_label)

            # b) Number of business days in the period
            #    (you said the function should receive the two dates)
            business_days = bd.getbusinessdays(start_dt, end_dt)

            # c) Guard against division‑by‑zero (empty quarter)
            if business_days == 0:
                daily_avg = 0.0
            else:
                daily_avg = round(row['Unit'] / business_days, 1)

            # d) Assemble a one‑row DataFrame and concatenate
            one_row = pd.DataFrame({
                'Quarter'      : [quarter_label],
                'Year'         : [year_val],
                'Total'        : [row['Unit']],
                'BusinessDays' : [business_days],
                'DailyAverage' : [daily_avg],
                'StartDate'    : [start_dt],
                'EndDate'      : [end_dt]
            })
            df_report = pd.concat([df_report, one_row], ignore_index=True)

        # --------------------------------------------------------------
        # 4️⃣ Sort, preview current‑year rows, and write the CSV
        df_report = df_report.sort_values(by=['Year', 'Quarter'], ascending=True)

        # Handy debug view – shows only the rows for the current calendar year
        print(df_report[df_report['Year'] == now.year])

        # Export – header written automatically, index omitted
        df_report.to_csv(output_file, index=False)
        print(f"File saved to {output_file}")

    except Exception as e:
        tmpl = "An exception of type {0} occurred. Arguments:\n{1!r}"
        msg = tmpl.format(type(e).__name__, e.args)
        print(msg)


def quartervslast3quarters():
  output_file= os.path.join(app_path,r'output\quarterstep1.csv')
  f = open(output_file,'w+',newline='')
  now = datetime.datetime.now()
  global businessdays
  global iyear
    
  try:
    businessdays = 0
    iyear = 0
    squarter = input("Quarter (ie Q12025):")
    dfCombined = pd.DataFrame(columns = ['Year','LocationName','ProcedureCategory','Region','Unit'],index=[0,1,2,3])
    

    daily1 = daily.Daily()
      
    for yr, q, start, end in last_three_quarters_from_input(squarter):      
      print(f"  Q{q} {yr}:  {start} → {end}")
        
      if iyear == 0:
          iyear = yr
          iquarter = q
          istart = start
          iend = end
            
      #dataframe for this year
      df = daily1.databydaterange(start, end)
      df = pd.DataFrame(df).reset_index()
      
      #dataframe for this year #Group by Year, Location, ProcedureCategory  
      df = df.groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()
      print(df)
      dfCombined = pd.concat([df,dfCombined])
      
    #get this year\month businessdays
    businessdays = bd.getbusinessdays(start,end)
    print(businessdays)
      
    #dataframe for budget
    budget1 = budget.Budget(0,iyear) 
    budgetdf = budget1.getquarterbudgetdf(iquarter).groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum() #uncomment to add budget
    #budgetdf = pd.DataFrame(columns=['LocationName','ProcedureCategory','Year','Month','Unit']) #Empty DataFrame; #comment out if budget is enabled
    #print(budgetdf)
    
    dfCombined = pd.concat([budgetdf,dfCombined])
    #print(dfCombined)    
      
    #Save to csv
    dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print("File saved to ",output_file)
    
    df_Final = dfCombined.pivot_table(index=['Region','LocationName'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
    df_Region = dfCombined.pivot_table(index=['Region'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
    df_Totals = dfCombined.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
     
    cols1 = df_Final.columns.tolist()
    cols2 = df_Totals.columns.tolist()

    #Dataframe with difference compared to previous year
    print('Difference = (ThisYear - Budget) / Budget')
    if budgetdf.empty != True:
        df_Final['Vol_Var'] = round((df_Final.iloc[:,2] - df_Final.iloc[:,3]),3)
        df_Final['Pct_Var'] = round(((df_Final.iloc[:,2] - df_Final.iloc[:,3])/df_Final.iloc[:,3]),3) * 100
          
        df_Region['Vol_Var'] = round((df_Region.iloc[:,2] - df_Region.iloc[:,3]),3)
        df_Region['Pct_Var'] = round(((df_Region.iloc[:,2] - df_Region.iloc[:,3])/df_Region.iloc[:,3]),3) * 100
          
        df_Totals['Vol_Var'] = round((df_Totals.iloc[:,2] - df_Totals.iloc[:,3]),3)
        df_Totals['Pct_Var'] = round(((df_Totals.iloc[:,2] - df_Totals.iloc[:,3])/df_Totals.iloc[:,3]),3) * 100
    else:    
        print('Budget Empty')
          
    df_Totals['Region'] = ''
    df_Totals['LocationName'] = 'TOTAL'
    df_Totals[cols2] = df_Totals[cols2].astype(int).applymap(lambda x:f'{x:,}')
      
    df5 = df_Totals.set_index(['Region','LocationName'])
      
    df_Final[cols1] = df_Final[cols1].astype(int).applymap(lambda x:f'{x:,}')      
    df5 = pd.concat([df_Final,df5]).fillna('-')      
    df5['Vol_Var'] = df5['Vol_Var'].apply(lambda x:'{:,}'.format(x))
      
    print('\n',df5)

    return dfCombined
      
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)


def quarterstep1():
  output_file= os.path.join(app_path,r'output\quarterstep1.csv')
  f = open(output_file,'w+',newline='')
  now = datetime.now()
  global businessdays
  global iyear
    
  try:
    businessdays = 0
    iyear = 0
    squarter = input("Quarter (ie Q12025):")
    dfCombined = pd.DataFrame(columns = ['Year','LocationName','ProcedureCategory','Region','Unit'])
    dfCombined = dfCombined.groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()
    

    daily1 = daily.Daily()
      
    for yr, q, start, end in same_quarter_last_three_years(squarter):
      print(f"  Q{q} {yr}:  {start} → {end}")
        
      if iyear == 0:
          iyear = yr #input year
          iquarter = q #input quarter
          istart = start
          iend = end
          print(iyear,iquarter,istart,iend)
            
      #dataframe for this year
      df = daily1.databydaterange(start, end)
      df = pd.DataFrame(df)
      
      #dataframe for this year #Group by Year, Location, ProcedureCategory  
      df = df.groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum()
      #print(df)
      dfCombined = pd.concat([df,dfCombined])
      
    #get this year\month businessdays
    businessdays = bd.getbusinessdays(start,end)
    print(businessdays)
      
    #dataframe for budget
    budget1 = budget.Budget(0,iyear) 
    budgetdf = budget1.getquarterbudgetdf(iquarter).groupby(['Year','LocationName','ProcedureCategory','Region'])['Unit'].sum() #uncomment to add budget
    #budgetdf = pd.DataFrame(columns=['LocationName','ProcedureCategory','Year','Month','Unit']) #Empty DataFrame; #comment out if budget is enabled
    #print(budgetdf)
    
    dfCombined = pd.concat([dfCombined,budgetdf])
    #print(dfCombined)    
    
    dfCombined = dfCombined.reset_index()
    
    #Save to csv
    dfCombined.to_csv(f,sep=',',mode='w+',line_terminator=None)
    print("File saved to ",output_file)
    
    df_Final = dfCombined.pivot_table(index=['Region','LocationName'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
    df_Region = dfCombined.pivot_table(index=['Region'],values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
    df_Totals = dfCombined.pivot_table(values='Unit', columns='Year', fill_value=0, aggfunc=np.sum)
     
    cols1 = df_Final.columns.tolist()
    cols2 = df_Totals.columns.tolist()

    #Dataframe with difference compared to previous year
    print('Difference = (ThisYear - Budget) / Budget')
    if budgetdf.empty != True:
        df_Final['Vol_Var'] = round((df_Final.iloc[:,2] - df_Final.iloc[:,3]),3)
        df_Final['Pct_Var'] = round(((df_Final.iloc[:,2] - df_Final.iloc[:,3])/df_Final.iloc[:,3]),3) * 100
          
        df_Region['Vol_Var'] = round((df_Region.iloc[:,2] - df_Region.iloc[:,3]),3)
        df_Region['Pct_Var'] = round(((df_Region.iloc[:,2] - df_Region.iloc[:,3])/df_Region.iloc[:,3]),3) * 100
          
        df_Totals['Vol_Var'] = round((df_Totals.iloc[:,2] - df_Totals.iloc[:,3]),3)
        df_Totals['Pct_Var'] = round(((df_Totals.iloc[:,2] - df_Totals.iloc[:,3])/df_Totals.iloc[:,3]),3) * 100
    else:    
        print('Budget Empty')
          
    df_Totals['Region'] = ''
    df_Totals['LocationName'] = 'TOTAL'
    df_Totals[cols2] = df_Totals[cols2].astype(int).applymap(lambda x:f'{x:,}')
      
    df5 = df_Totals.set_index(['Region','LocationName'])
      
    df_Final[cols1] = df_Final[cols1].astype(int).applymap(lambda x:f'{x:,}')      
    df5 = pd.concat([df_Final,df5]).fillna('-')      
    df5['Vol_Var'] = df5['Vol_Var'].apply(lambda x:'{:,}'.format(x))
      
    print('\n',df5)

    return dfCombined
      
  except Exception as e:
    template = "An exception of type {0} occurred. Arguments: \n{1!r}"
    message = template.format(type(e).__name__,e.args)
    print(message)


def _quarter_range(year: int, q: int) -> Tuple[date, date]:
    """Return (first_day, last_day) for the supplied year/quarter."""
    start_month = 3 * (q - 1) + 1          # 1, 4, 7, 10
    end_month   = start_month + 2

    start = date(year, start_month, 1)
    last_day = calendar.monthrange(year, end_month)[1]
    end   = date(year, end_month, last_day)
    return start, end


# ----------------------------------------------------------------------
def _parse_quarter_input(q_input: str) -> Tuple[int, int]:
    """
    Extract (year, quarter_number) from strings like:
        "Q1 2025", "Q12025", "q2 2023", "2025Q1"
    Whitespace and case are ignored.
    """
    s = q_input.replace(" ", "").upper()

    if s.startswith("Q"):                     # "Q<N><YYYY>"
        quarter = int(s[1])
        year = int(s[2:])
    elif s.endswith("Q"):                     # "<YYYY>Q<N>"
        quarter = int(s[-1])
        year = int(s[:-1])
    else:
        raise ValueError(
            f'Cannot parse "{q_input}". Expected "Q1 2025" or "2025Q1".'
        )
    if not 1 <= quarter <= 4:
        raise ValueError(f"Quarter must be 1‑4, got {quarter}")
    return year, quarter


# ----------------------------------------------------------------------
def same_quarter_last_three_years(q_input: str) -> List[Tuple[int, int, date, date]]:
    """
    Given a quarter string (e.g. "Q1 2025"), return the date ranges for that
    quarter in the input year and the two preceding years.

    Returns
    -------
    List[Tuple[int, int, date, date]]
        [(year, quarter, start_date, end_date), ...] ordered newest→oldest.
    """
    year, quarter = _parse_quarter_input(q_input)

    result: List[Tuple[int, int, date, date]] = []
    for y in (year, year - 1, year - 2):
        start, end = _quarter_range(y, quarter)
        result.append((y, quarter, start, end))

    return result


# ----------------------------------------------------------------------
# Main: generate the quarter identifiers (and optionally the date ranges)
def quarters_last_three_years(
    quarter_input: str,
    include_dates: bool = False
) ->List[Union[Tuple[str, date, date], str]]:
    """
    Given a quarter string (e.g., "Q1 2025"), produce every quarter
    from that quarter back three calendar years (36 months).

    Parameters
    ----------
    quarter_input : str
        The quarter you start from.
    include_dates : bool, default=False
        If True, each list element is a tuple
        (quarter_id, start_date, end_date);
        otherwise each element is just the quarter identifier string.

    Returns
    -------
    List[...]
        Ordered from newest to oldest.
    """
    year, q = _parse_quarter(quarter_input)

    # We need 3 years × 4 quarters = 12 entries
    total_quarters = 12
    result: List[Tuple[str, date, date] | str] = []

    for _ in range(total_quarters):
        quarter_id = f"Q{q} {year}"
        if include_dates:
            start, end = _quarter_range(year, q)
            result.append((quarter_id, start, end))
        else:
            result.append(quarter_id)

        # Step back one quarter
        q -= 1
        if q == 0:          # crossing from Q1 → previous year's Q4
            q = 4
            year -= 1

    return result


# ----------------------------------------------------------------------
# Demo
"""if __name__ == "__main__":
    # Example 1 – just the identifiers
    print("Identifiers only:")
    for qid in quarters_last_three_years("Q1 2025"):
        print("  ", qid)

    # Example 2 – identifiers + date ranges
    print("\nWith date ranges:")
    for qid, start, end in quarters_last_three_years("Q1 2025", include_dates=True):
        print(f"  {qid}: {start} → {end}")
"""






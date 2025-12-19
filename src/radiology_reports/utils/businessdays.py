import logging
import datetime as dt
from datetime import date
from calendar import monthrange
from typing import List, Optional
from pandas.tseries.offsets import CustomBusinessDay
import numpy as np
import pandas as pd
import os

# Comment out or remove if 'daily' is not needed; assume it's custom and optional
# from daily import Daily # Uncomment if required for years()

from radiology_reports.data.workload import get_connection  # Use existing connection manager from workload.py

logger = logging.getLogger(__name__)

def is_business_day(d: date) -> bool:
    """
    Checks if a date is a business day (weekday).
    """
    return d.weekday() < 5

def get_holidays() -> List[date]:
    """
    Fetches holidays from the database using the existing get_connection from workload.py.
    """
    try:
        with get_connection() as conn:
            query = "SELECT date FROM Holidays;"
            data = pd.read_sql_query(query, conn)
            holidays = [x.date() if isinstance(x, dt.datetime) else x for x in data['date']]
            logger.info(f"Fetched {len(holidays)} holidays from database.")
            return holidays
    except Exception as e:
        logger.error(f"Error fetching holidays: {e}")
        raise

def get_business_days(start: date, end: date, holidays: Optional[List[date]] = None) -> int:
    """
    Calculates the number of business days between start and end, excluding holidays.
    """
    try:
        if holidays is None:
            holidays = get_holidays()
        bdc = np.busdaycalendar(holidays=np.array(holidays, dtype='datetime64[D]'))
        freq = CustomBusinessDay(calendar=bdc)
        bdays = pd.bdate_range(start, end, freq=freq)
        logger.debug(f"Business days between {start} and {end}: {len(bdays)}")
        return len(bdays)
    except Exception as e:
        logger.error(f"Error calculating business days: {e}")
        raise

def get_mtd_business_days(end_date: date) -> int:
    """
    Gets business days month-to-date up to end_date.
    """
    month_start = end_date.replace(day=1)
    return get_business_days(month_start, end_date)

def get_ytd_business_days(end_date: date) -> pd.DatetimeIndex:
    """
    Gets business days year-to-date up to end_date.
    """
    year_start = end_date.replace(month=1, day=1)
    return pd.bdate_range(year_start, end_date, freq=CustomBusinessDay(calendar=np.busdaycalendar(holidays=get_holidays())))

def get_months_business_days(start: date, end: date) -> pd.DataFrame:
    """
    Gets business days per month between start and end.
    """
    try:
        holidays = get_holidays()
        bdc = np.busdaycalendar(holidays=np.array(holidays, dtype='datetime64[D]'))
        freq = CustomBusinessDay(calendar=bdc)
        bdays = pd.DataFrame(pd.bdate_range(start, end, freq=freq))
        bdays['Year'] = pd.to_datetime(bdays[0]).dt.year
        bdays['Month'] = pd.to_datetime(bdays[0]).dt.month
        bdays = pd.pivot_table(bdays, index=['Month', 'Year'], values=0, aggfunc='count')
        bdays.rename(columns={0: 'BusinessDays'}, inplace=True)
        return bdays
    except Exception as e:
        logger.error(f"Error calculating monthly business days: {e}")
        raise

def get_half_days(df: pd.DataFrame) -> np.ndarray:
    """
    Gets hardcoded half days based on years in the DataFrame.
    """
    try:
        df = df.dropna(subset=['Year'])
        years = df['Year'].unique().astype(int)
        half_days = np.array([])
        for iyear in years:
            half_days = np.append(half_days, [
                dt.datetime(2017, 11, 24), dt.datetime(2018, 11, 23),  # Thanksgiving
                dt.datetime(2019, 11, 29), dt.datetime(2020, 11, 27),  # Thanksgiving
                dt.datetime(iyear, 12, 24),  # Christmas
                dt.datetime(iyear, 12, 31)   # New Years
            ])
        return half_days
    except Exception as e:
        logger.error(f"Error getting half days: {e}")
        raise

def generate_years_report(output_file: str = 'output/businessdays-years.csv'):
    pass
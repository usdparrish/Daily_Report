import pandas as pd
import numpy as np
from pmdarima import auto_arima
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
import os
import warnings
warnings.filterwarnings("ignore")

def load_and_prepare_data(historical_csv, scheduled_csv=None, budget_csv=None):
    """Load and prepare data, downsample to weekly"""
    if not os.path.exists(historical_csv):
        raise FileNotFoundError(f"Historical CSV file '{historical_csv}' not found.")
    hist_df = pd.read_csv(historical_csv, parse_dates=['date'])
    required_columns = {'date', 'location', 'modality', 'exam_count'}
    if not required_columns.issubset(hist_df.columns):
        missing = required_columns - set(hist_df.columns)
        raise ValueError(f"Historical CSV missing required columns: {missing}")
    
    hist_df['day_of_week'] = hist_df['date'].dt.dayofweek
    
    # Aggregate to weekly totals per location/modality
    hist_ts = hist_df.groupby([
        pd.Grouper(key='date', freq='W-MON'), # Weekly, starting Monday
        'location', 'modality'
    ])['exam_count'].sum().reset_index()
    
    # Calculate historical capacity (weekly max)
    capacity_df = hist_ts.groupby(['location', 'modality'])['exam_count'].max().reset_index()
    capacity_df = capacity_df.rename(columns={'exam_count': 'max_capacity'})
    print("\nCalculated Weekly Historical Capacities:")
    print(capacity_df)
    
    # Calculate day-of-week effects (from daily data)
    dow_effects = hist_df.groupby('day_of_week')['exam_count'].mean().to_dict()
    print("\nDay-of-Week Effects (Average Daily Exams):")
    for dow, avg in dow_effects.items():
        print(f"Day {dow} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]}): {avg:.2f}")
    
    # Load scheduled data (daily, not weekly)
    scheduled_df = None
    if scheduled_csv and os.path.exists(scheduled_csv):
        scheduled_df = pd.read_csv(scheduled_csv, parse_dates=['date'])
        scheduled_columns = {'date', 'location', 'modality', 'scheduled_count'}
        if not scheduled_columns.issubset(scheduled_df.columns):
            missing = scheduled_columns - set(scheduled_df.columns)
            raise ValueError(f"Scheduled CSV missing required columns: {missing}")
    else:
        print("Warning: No scheduled exams CSV provided.")
    
    # Load budget data
    budget_df = None
    if budget_csv and os.path.exists(budget_csv):
        budget_df = pd.read_csv(budget_csv)
        budget_columns = {'location', 'modality', 'budget_count'}
        if not budget_columns.issubset(budget_df.columns):
            missing = budget_columns - set(budget_df.columns)
            raise ValueError(f"Budget CSV missing required columns: {missing}")
    
    return hist_ts, scheduled_df, budget_df, capacity_df, dow_effects

def train_sarima_model(args):
    """Train a SARIMA model on weekly data"""
    ts_data, location, modality = args
    combo_data = ts_data[(ts_data['location'] == location) & (ts_data['modality'] == modality)]
    if len(combo_data) < 5: # Minimum for weekly data
        print(f"Warning: Insufficient data for {location}, {modality}. Skipping SARIMA.")
        return (location, modality), (None, None)
    
    combo_ts = combo_data.set_index('date')['exam_count']
    combo_ts = combo_ts.asfreq('W-MON', fill_value=0) # Weekly frequency
    
    if len(combo_ts) > 4: # ~1 month test period
        train = combo_ts[:-4]
        test = combo_ts[-4:]
    else:
        train = combo_ts
        test = None
    
    try:
        model = auto_arima(train, seasonal=True, m=52, # Annual seasonality for weekly data
                          start_p=0, start_q=0, max_p=2, max_q=2,
                          start_P=0, start_Q=0, max_P=1, max_Q=1,
                          d=1, D=1,
                          suppress_warnings=True, stepwise=True,
                          maxiter=10) # Minimal iterations
        fitted_model = model.fit(train)
        
        print(f"\nSARIMA Model for {location}, {modality}:")
        print(f"Order: {model.order}")
        print(f"Seasonal Order: {model.seasonal_order}")
        
        if test is not None:
            forecast = fitted_model.predict(n_periods=4)
            mae = np.mean(np.abs(forecast - test))
            mse = np.mean((forecast - test) ** 2)
            print(f"Test MAE (4 weeks): {mae:.4f}")
            print(f"Test MSE (4 weeks): {mse:.4f}")
        
        return (location, modality), (fitted_model, train.index[-1])
    except Exception as e:
        print(f"Error fitting SARIMA for {location}, {modality}: {e}")
        return (location, modality), (None, None)

def is_holiday(date, holidays):
    """Check if a date is a holiday"""
    return date.strftime('%Y-%m-%d') in holidays

def predict_future_exams(models, start_date, days_ahead, scheduled_df, budget_df, capacity_df, dow_effects):
    """Predict exam counts using weekly SARIMA, adjusted to daily"""
    if not models:
        print("No models trained. Cannot predict.")
        return pd.DataFrame(columns=['date', 'location', 'modality', 'scheduled_count', 
                                    'predicted_additional', 'max_capacity', 'total_predicted', 
                                    'budget_count', 'variance', 'is_holiday'])
    
    start_date = pd.to_datetime(start_date)
    future_dates = pd.date_range(start=start_date, periods=days_ahead, freq='D')
    
    holidays = {'2025-01-01', '2025-07-04', '2025-12-25'}
    
    predictions = []
    for date in future_dates:
        day_scheduled = scheduled_df[scheduled_df['date'] == date] if scheduled_df is not None else pd.DataFrame()
        
        dow = date.dayofweek
        dow_factor = dow_effects.get(dow, 1.0) / max(dow_effects.values()) if dow_effects else 1.0
        holiday = is_holiday(date, holidays)
        is_weekend = dow in [5, 6]
        
        scheduled_combos = set()
        if not day_scheduled.empty:
            for _, row in day_scheduled.iterrows():
                location = row['location']
                modality = row['modality']
                scheduled_count = row['scheduled_count']
                scheduled_combos.add((location, modality))
                
                model_key = (location, modality)
                model_info = models.get(model_key, (None, None))
                model, last_train_date = model_info
                
                pred_additional = 0
                if model and last_train_date:
                    weeks_ahead = (date - last_train_date).days // 7 + 1 # Convert days to weeks
                    if weeks_ahead > 0:
                        forecast = model.predict(n_periods=weeks_ahead)
                        weekly_pred = max(0, int(round(forecast[-1] / 7))) # Daily avg from weekly
                        pred_additional = int(weekly_pred * dow_factor)
                
                capacity_row = capacity_df[
                    (capacity_df['location'] == location) & 
                    (capacity_df['modality'] == modality)
                ]
                max_capacity = capacity_row['max_capacity'].iloc[0] if not capacity_row.empty else float('inf')
                
                budget_count = 0 if (budget_df is None or is_weekend) else (
                    budget_df[
                        (budget_df['location'] == location) & 
                        (budget_df['modality'] == modality)
                    ]['budget_count'].iloc[0] if not budget_df[
                        (budget_df['location'] == location) & 
                        (budget_df['modality'] == modality)
                    ].empty else None
                )
                
                if scheduled_count == 0:
                    total_predicted = 0
                elif holiday:
                    total_predicted = scheduled_count
                else:
                    total_unconstrained = scheduled_count + pred_additional
                    total_predicted = min(total_unconstrained, max_capacity, int(budget_count * 1.1)) if budget_count else min(total_unconstrained, max_capacity)
                
                variance = total_predicted - budget_count if budget_count is not None else None
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'location': location,
                    'modality': modality,
                    'scheduled_count': scheduled_count,
                    'predicted_additional': pred_additional,
                    'max_capacity': max_capacity if max_capacity != float('inf') else 'N/A',
                    'total_predicted': total_predicted,
                    'budget_count': budget_count if budget_count is not None else 'N/A',
                    'variance': variance if variance is not None else 'N/A',
                    'is_holiday': holiday
                })
        
        if budget_df is not None and not holiday and not is_weekend:
            for _, budget_row in budget_df.iterrows():
                location = budget_row['location']
                modality = budget_row['modality']
                if (location, modality) in scheduled_combos:
                    continue
                
                model_key = (location, modality)
                model_info = models.get(model_key, (None, None))
                model, last_train_date = model_info
                
                pred_additional = 0
                if model and last_train_date:
                    weeks_ahead = (date - last_train_date).days // 7 + 1
                    if weeks_ahead > 0:
                        forecast = model.predict(n_periods=weeks_ahead)
                        weekly_pred = max(0, int(round(forecast[-1] / 7))) # Daily avg
                        pred_additional = int(weekly_pred * dow_factor)
                
                capacity_row = capacity_df[
                    (capacity_df['location'] == location) & 
                    (capacity_df['modality'] == modality)
                ]
                max_capacity = capacity_row['max_capacity'].iloc[0] if not capacity_row.empty else float('inf')
                
                budget_count = budget_row['budget_count']
                
                total_unconstrained = max(1, pred_additional)
                total_predicted = min(total_unconstrained, max_capacity, int(budget_count * 1.1))
                
                variance = total_predicted - budget_count
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'location': location,
                    'modality': modality,
                    'scheduled_count': 'N/A',
                    'predicted_additional': pred_additional,
                    'max_capacity': max_capacity if max_capacity != float('inf') else 'N/A',
                    'total_predicted': total_predicted,
                    'budget_count': budget_count,
                    'variance': variance,
                    'is_holiday': holiday
                })
    
    return pd.DataFrame(predictions)

def print_daily_summary(predictions):
    """Print a summary of total scheduled, predicted, budget, and variance per day"""
    if predictions.empty:
        print("No predictions to summarize.")
        return
    
    predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
    
    daily_summary = predictions.groupby('date').agg({
        'scheduled_count_numeric': 'sum',
        'total_predicted': 'sum',
        'budget_count': lambda x: x.sum() if x.notna().any() else np.nan
    }).reset_index()
    daily_summary['variance'] = daily_summary['total_predicted'] - daily_summary['budget_count']
    daily_summary = daily_summary.rename(columns={'scheduled_count_numeric': 'total_scheduled'})
    
    print("\nDaily Summary of Total Scheduled, Predicted Exams vs Budget:")
    print(daily_summary.to_string(index=False))

def save_predictions(predictions, output_file):
    """Save predictions and daily summary to CSV files"""
    predictions.to_csv(output_file, index=False)
    print(f"Predictions saved to '{output_file}'")
    
    if not predictions.empty:
        predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
        daily_summary = predictions.groupby('date').agg({
            'scheduled_count_numeric': 'sum',
            'total_predicted': 'sum',
            'budget_count': lambda x: x.sum() if x.notna().any() else np.nan
        }).reset_index()
        daily_summary['variance'] = daily_summary['total_predicted'] - daily_summary['budget_count']
        daily_summary = daily_summary.rename(columns={'scheduled_count_numeric': 'total_scheduled'})
        summary_file = output_file.replace('.csv', '_daily_summary.csv')
        daily_summary.to_csv(summary_file, index=False)
        print(f"Daily summary saved to '{summary_file}'")

if __name__ == "__main__":
    historical_csv = "exam_data.csv"
    scheduled_csv = "scheduled_exams.csv"
    budget_csv = "budget_exams.csv"
    
    try:
        hist_ts, scheduled_df, budget_df, capacity_df, dow_effects = load_and_prepare_data(
            historical_csv, scheduled_csv, budget_csv
        )
        
        # Train SARIMA models with parallel processing
        combos = [(hist_ts, loc, mod) for loc, mod in hist_ts.groupby(['location', 'modality']).groups.keys()]
        print(f"Training SARIMA for {len(combos)} combos using {cpu_count()} cores...")
        with Pool(processes=cpu_count()) as pool:
            results = pool.map(train_sarima_model, combos)
        
        models = dict(results)
        
        start_date = '2025-03-01'
        days_ahead = 7
        
        predictions = predict_future_exams(
            models, 
            start_date, 
            days_ahead, 
            scheduled_df,
            budget_df,
            capacity_df,
            dow_effects
        )
        
        print("\nPredicted Exam Counts:")
        print(predictions.sort_values(by=['date', 'location', 'modality']))
        
        print_daily_summary(predictions)
        save_predictions(predictions, "exam_predictions.csv")
    
    except Exception as e:
        print(f"Error: {e}")


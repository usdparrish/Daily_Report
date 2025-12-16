import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
import os
import warnings

warnings.filterwarnings("ignore")

def load_and_prepare_data(historical_csv, scheduled_csv=None, budget_csv=None):
    """Load and prepare data for Prophet with procedure_duration as total daily duration and num_rooms"""
    if not os.path.exists(historical_csv):
        raise FileNotFoundError(f"Historical CSV file '{historical_csv}' not found.")
    
    hist_df = pd.read_csv(historical_csv)
    required_columns = {'date', 'location', 'modality', 'exam_count', 'procedure_duration', 'num_rooms'}
    if not required_columns.issubset(hist_df.columns):
        missing = required_columns - set(hist_df.columns)
        raise ValueError(f"Historical CSV missing required columns: {missing}")
    
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    hist_df['day_of_week'] = hist_df['date'].dt.dayofweek
    hist_df['procedure_duration'] = pd.to_numeric(hist_df['procedure_duration'], errors='coerce')
    
    hist_ts = hist_df.groupby(['date', 'location', 'modality']).agg({
        'exam_count': 'sum',
        'procedure_duration': 'sum',
        'num_rooms': 'max'
    }).reset_index()
    hist_ts = hist_ts.rename(columns={'date': 'ds', 'exam_count': 'y'})
    
    hist_ts['duration_per_room'] = hist_ts['procedure_duration'] / hist_ts['num_rooms']
    capacity_df = hist_ts.groupby(['location', 'modality']).agg({
        'duration_per_room': 'max',
        'num_rooms': 'max'
    }).reset_index()
    capacity_df['max_duration_capacity'] = capacity_df['duration_per_room'] * capacity_df['num_rooms']
    capacity_df = capacity_df[['location', 'modality', 'num_rooms', 'max_duration_capacity']]
    print("\nCalculated Daily Historical Duration Capacities (minutes) with Room Consideration:")
    print(capacity_df)
    
    dow_effects = hist_df.groupby('day_of_week')['exam_count'].mean().to_dict()
    print("\nDay-of-Week Effects (Average Daily Exams):")
    for dow, avg in dow_effects.items():
        print(f"Day {dow} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]}): {avg:.2f}")
    
    scheduled_df = None
    if scheduled_csv and os.path.exists(scheduled_csv):
        scheduled_df = pd.read_csv(scheduled_csv)
        scheduled_df['date'] = pd.to_datetime(scheduled_df['date']).dt.date
        scheduled_columns = {'date', 'location', 'modality', 'scheduled_count', 'procedure_duration', 'num_rooms'}
        if not scheduled_columns.issubset(scheduled_df.columns):
            missing = scheduled_columns - set(scheduled_df.columns)
            raise ValueError(f"Scheduled CSV missing required columns: {missing}")
        scheduled_df['procedure_duration'] = pd.to_numeric(scheduled_df['procedure_duration'], errors='coerce')
    else:
        print("Warning: No scheduled exams CSV provided.")
    
    budget_df = None
    if budget_csv and os.path.exists(budget_csv):
        budget_df = pd.read_csv(budget_csv)
        budget_columns = {'location', 'modality', 'budget_count'}
        if not budget_columns.issubset(budget_df.columns):
            missing = budget_columns - set(budget_df.columns)
            raise ValueError(f"Budget CSV missing required columns: {missing}")
    
    return hist_ts, scheduled_df, budget_df, capacity_df, dow_effects

def train_prophet_model(args):
    """Train a Prophet model without plotly"""
    ts_data, location, modality = args
    combo_data = ts_data[(ts_data['location'] == location) & (ts_data['modality'] == modality)]
    if len(combo_data) < 10:
        print(f"Warning: Insufficient data for {location}, {modality}. Skipping Prophet.")
        return (location, modality), (None, None)
    
    combo_ts = combo_data[['ds', 'y']].copy()
    
    if len(combo_ts) > 7:
        train = combo_ts[:-7]
        test = combo_ts[-7:]
    else:
        train = combo_ts
        test = None
    
    try:
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False,
                       holidays=pd.DataFrame({
                           'holiday': 'us_holidays',
                           'ds': pd.to_datetime(['2023-01-01', '2023-07-04', '2023-12-25',
                                                '2024-01-01', '2024-07-04', '2024-12-31']),
                           'lower_window': 0,
                           'upper_window': 0
                       }), 
                       mcmc_samples=0, 
                       interval_width=0)
        model.fit(train)
        
        if test is not None:
            # Use test dates directly for prediction
            future = pd.DataFrame({'ds': test['ds']})
            forecast = model.predict(future)
            forecast_test = forecast
            
            # Detailed debugging
            print(f"\nDebugging Prophet Model for {location}, {modality}:")
            print(f"Train length: {len(train)}, Test length: {len(test)}")
            print(f"Test dates: {test['ds'].tolist()}")
            print(f"Test y: {test['y'].tolist()}")
            print(f"Forecast dates: {forecast_test['ds'].tolist()}")
            print(f"Forecast yhat: {forecast_test['yhat'].tolist()}")
            
            # Check for NaN or infinite values
            test_y = test['y'].values
            yhat = forecast_test['yhat'].values
            if np.any(np.isnan(test_y)) or np.any(np.isinf(test_y)):
                print(f"NaN or Inf in test['y']: {test_y}")
            if np.any(np.isnan(yhat)) or np.any(np.isinf(yhat)):
                print(f"NaN or Inf in forecast_test['yhat']: {yhat}")
            
            # Ensure lengths match
            if len(yhat) != len(test_y):
                print(f"Length mismatch: yhat={len(yhat)}, test_y={len(test_y)}")
                return (location, modality), (model, train['ds'].max())
            
            # Compute differences
            differences = yhat - test_y
            print(f"Differences (yhat - test['y']): {differences.tolist()}")
            
            # Calculate metrics
            mae = np.mean(np.abs(differences))
            mse = np.mean(differences ** 2)
            print(f"MAE calculation: np.mean(np.abs({differences.tolist()})) = {mae}")
            print(f"MSE calculation: np.mean({(differences ** 2).tolist()}) = {mse}")
            print(f"Test MAE (7 days): {mae:.4f}")
            print(f"Test MSE (7 days): {mse:.4f}")
        
        return (location, modality), (model, train['ds'].max())
    except Exception as e:
        print(f"Error fitting Prophet for {location}, {modality}: {e}")
        return (location, modality), (None, None)

def is_holiday(date, holidays):
    """Check if a date is a holiday"""
    return datetime.strftime(date, '%Y-%m-%d') in holidays

def predict_future_exams(models, start_date, days_ahead, scheduled_df, budget_df, capacity_df, dow_effects):
    """Predict exam counts with duration-based capacity, treating scheduled_count as future bookings"""
    if not models:
        print("No models trained. Cannot predict.")
        return pd.DataFrame(columns=['date', 'location', 'modality', 'scheduled_count', 'num_rooms',
                                    'predicted_additional', 'max_duration_capacity', 'total_predicted',
                                    'total_duration_predicted', 'budget_count', 'variance', 'is_holiday'])
    
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
                total_scheduled_duration = row['procedure_duration']
                num_rooms = row['num_rooms']
                scheduled_combos.add((location, modality))
                
                model_key = (location, modality)
                model_info = models.get(model_key, (None, None))
                model, last_train_date = model_info
                
                capacity_row = capacity_df[
                    (capacity_df['location'] == location) &
                    (capacity_df['modality'] == modality)
                ]
                max_duration_capacity = capacity_row['max_duration_capacity'].iloc[0] if not capacity_row.empty else float('inf')
                num_rooms_capacity = capacity_row['num_rooms'].iloc[0] if not capacity_row.empty else num_rooms
                
                budget_count = 0 if (budget_df is None or is_weekend) else (
                    budget_df[
                        (budget_df['location'] == location) &
                        (budget_df['modality'] == modality)
                    ]['budget_count'].iloc[0] if not budget_df[
                        (budget_df['location'] == location) &
                        (budget_df['modality'] == modality)
                    ].empty else None
                )
                
                hist_avg_duration_per_room = hist_ts[
                    (hist_ts['location'] == location) &
                    (hist_ts['modality'] == modality)
                ]['procedure_duration'].mean() / (
                    hist_ts[
                        (hist_ts['location'] == location) &
                        (hist_ts['modality'] == modality)
                    ]['y'].mean() * hist_ts[
                        (hist_ts['location'] == location) &
                        (hist_ts['modality'] == modality)
                    ]['num_rooms'].mean()
                ) if not hist_ts[
                    (hist_ts['location'] == location) &
                    (hist_ts['modality'] == modality)
                ].empty else 30
                
                if scheduled_count == 0:
                    total_predicted = 0
                    total_duration_predicted = 0
                    pred_additional = 0
                elif holiday:
                    total_predicted = scheduled_count
                    total_duration_predicted = total_scheduled_duration
                    pred_additional = 0
                else:
                    # Predict total exams with Prophet
                    if model and last_train_date:
                        days_ahead = (date - last_train_date).days
                        if days_ahead > 0:
                            future = model.make_future_dataframe(periods=days_ahead)
                            forecast = model.predict(future)
                            pred_total_raw = max(0, int(round(forecast['yhat'].iloc[-1])))
                            pred_total = int(pred_total_raw * dow_factor)
                            # Additional exams beyond scheduled
                            pred_additional = max(0, pred_total - scheduled_count)
                            # Cap by remaining capacity
                            remaining_duration = max(0, max_duration_capacity - total_scheduled_duration)
                            max_additional_exams = int(remaining_duration / (hist_avg_duration_per_room * num_rooms))
                            pred_additional = min(pred_additional, max_additional_exams)
                        else:
                            pred_additional = 0
                    else:
                        pred_additional = 0
                    
                    total_predicted = scheduled_count + pred_additional
                    total_duration_predicted = total_scheduled_duration + (pred_additional * hist_avg_duration_per_room * num_rooms)
                    
                    # Apply budget constraint, respecting capacity
                    if budget_count:
                        budget_duration = budget_count * hist_avg_duration_per_room * num_rooms_capacity * 1.1
                        if total_duration_predicted > budget_duration:
                            excess_duration = total_duration_predicted - budget_duration
                            reduced_additional = max(0, pred_additional - int(excess_duration / (hist_avg_duration_per_room * num_rooms_capacity)))
                            total_predicted = scheduled_count + reduced_additional
                            total_duration_predicted = total_scheduled_duration + (reduced_additional * hist_avg_duration_per_room * num_rooms_capacity)
                    
                    # Final capacity check
                    if total_duration_predicted > max_duration_capacity:
                        excess_duration = total_duration_predicted - max_duration_capacity
                        reduced_additional = max(0, pred_additional - int(excess_duration / (hist_avg_duration_per_room * num_rooms_capacity)))
                        total_predicted = scheduled_count + reduced_additional
                        total_duration_predicted = total_scheduled_duration + (reduced_additional * hist_avg_duration_per_room * num_rooms_capacity)
                
                variance = total_predicted - budget_count if budget_count is not None else None
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'location': location,
                    'modality': modality,
                    'scheduled_count': scheduled_count,
                    'num_rooms': num_rooms,
                    'predicted_additional': pred_additional,
                    'max_duration_capacity': max_duration_capacity if max_duration_capacity != float('inf') else 'N/A',
                    'total_predicted': total_predicted,
                    'total_duration_predicted': total_duration_predicted,
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
                
                capacity_row = capacity_df[
                    (capacity_df['location'] == location) &
                    (capacity_df['modality'] == modality)
                ]
                num_rooms = capacity_row['num_rooms'].iloc[0] if not capacity_row.empty else 1
                max_duration_capacity = capacity_row['max_duration_capacity'].iloc[0] if not capacity_row.empty else float('inf')
                
                hist_avg_duration_per_room = hist_ts[
                    (hist_ts['location'] == location) &
                    (hist_ts['modality'] == modality)
                ]['procedure_duration'].mean() / (
                    hist_ts[
                        (hist_ts['location'] == location) &
                        (hist_ts['modality'] == modality)
                    ]['y'].mean() * hist_ts[
                        (hist_ts['location'] == location) &
                        (hist_ts['modality'] == modality)
                    ]['num_rooms'].mean()
                ) if not hist_ts[
                    (hist_ts['location'] == location) &
                    (hist_ts['modality'] == modality)
                ].empty else 30
                
                model_key = (location, modality)
                model_info = models.get(model_key, (None, None))
                model, last_train_date = model_info
                
                budget_count = budget_row['budget_count']
                
                if model and last_train_date:
                    days_ahead = (date - last_train_date).days
                    if days_ahead > 0:
                        future = model.make_future_dataframe(periods=days_ahead)
                        forecast = model.predict(future)
                        pred_total_raw = max(0, int(round(forecast['yhat'].iloc[-1])))
                        pred_total = int(pred_total_raw * dow_factor)
                        pred_additional = pred_total # No scheduled_count here
                        # Cap by full capacity since no scheduled exams
                        max_additional_exams = int(max_duration_capacity / (hist_avg_duration_per_room * num_rooms))
                        pred_additional = min(pred_additional, max_additional_exams)
                    else:
                        pred_additional = 0
                else:
                    pred_additional = 0
                
                total_predicted = pred_additional
                total_duration_predicted = pred_additional * hist_avg_duration_per_room * num_rooms
                
                if budget_count:
                    budget_duration = budget_count * hist_avg_duration_per_room * num_rooms * 1.1
                    if total_duration_predicted > budget_duration:
                        total_predicted = int(budget_duration / (hist_avg_duration_per_room * num_rooms))
                        total_duration_predicted = total_predicted * hist_avg_duration_per_room * num_rooms
                
                if total_duration_predicted > max_duration_capacity:
                    total_predicted = int(max_duration_capacity / (hist_avg_duration_per_room * num_rooms))
                    total_duration_predicted = total_predicted * hist_avg_duration_per_room * num_rooms
                
                variance = total_predicted - budget_count
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'location': location,
                    'modality': modality,
                    'scheduled_count': 'N/A',
                    'num_rooms': num_rooms,
                    'predicted_additional': pred_additional,
                    'max_duration_capacity': max_duration_capacity if max_duration_capacity != float('inf') else 'N/A',
                    'total_predicted': total_predicted,
                    'total_duration_predicted': total_duration_predicted,
                    'budget_count': budget_count,
                    'variance': variance,
                    'is_holiday': holiday
                })
    
    return pd.DataFrame(predictions)

def print_daily_summary(predictions):
    """Print a summary including duration and rooms"""
    if predictions.empty:
        print("No predictions to summarize.")
        return
    
    predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
    
    daily_summary = predictions.groupby('date').agg({
        'scheduled_count_numeric': 'sum',
        'num_rooms': 'sum',
        'total_predicted': 'sum',
        'total_duration_predicted': 'sum',
        'budget_count': lambda x: x.sum() if x.notna().any() else np.nan
    }).reset_index()
    daily_summary['variance'] = daily_summary['total_predicted'] - daily_summary['budget_count']
    daily_summary = daily_summary.rename(columns={'scheduled_count_numeric': 'total_scheduled'})
    
    print("\nDaily Summary of Total Scheduled, Predicted Exams/Duration vs Budget (with Rooms):")
    print(daily_summary.to_string(index=False))

def save_predictions(predictions, output_file):
    """Save predictions and daily summary to CSV files"""
    predictions.to_csv(output_file, index=False)
    print(f"Predictions saved to '{output_file}'")
    
    if not predictions.empty:
        predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
        daily_summary = predictions.groupby('date').agg({
            'scheduled_count_numeric': 'sum',
            'num_rooms': 'sum',
            'total_predicted': 'sum',
            'total_duration_predicted': 'sum',
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
        
        combos = [(hist_ts, loc, mod) for loc, mod in hist_ts.groupby(['location', 'modality']).groups.keys()]
        print(f"Training Prophet for {len(combos)} combos using {cpu_count()} cores...")
        with Pool(processes=cpu_count()) as pool:
            results = pool.map(train_prophet_model, combos)
        
        models = dict(results)
        
        start_date = '2025-03-24'
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

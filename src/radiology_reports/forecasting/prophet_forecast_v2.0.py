import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from datetime import timedelta
from multiprocessing import Pool, cpu_count
import os
import warnings
import holidays
import matplotlib.pyplot as plt
from functools import lru_cache

warnings.filterwarnings("ignore")

@lru_cache(maxsize=365)
def is_holiday_cached(date_str, year=2025):
    return date_str in holidays.US(years=[year])

def load_and_prepare_data(historical_csv, scheduled_csv=None, budget_csv=None):
    """Load and prepare data efficiently"""
    if not os.path.exists(historical_csv):
        raise FileNotFoundError(f"Historical CSV file '{historical_csv}' not found.")
    
    hist_df = pd.read_csv(historical_csv, parse_dates=['date'])
    required_columns = {'date', 'location', 'modality', 'exam_count', 'procedure_duration', 'num_rooms'}
    if not required_columns.issubset(hist_df.columns):
        missing = required_columns - set(hist_df.columns)
        raise ValueError(f"Historical CSV missing required columns: {missing}")
    
    hist_df['procedure_duration'] = pd.to_numeric(hist_df['procedure_duration'], errors='coerce')
    
    hist_ts = (hist_df.groupby(['date', 'location', 'modality'])
               .agg({'exam_count': 'sum', 'procedure_duration': 'sum', 'num_rooms': 'max'})
               .reset_index()
               .rename(columns={'date': 'ds', 'exam_count': 'y'}))
    hist_ts['duration_per_exam'] = hist_ts['procedure_duration'] / hist_ts['y']  # Per-exam duration
    
    capacity_df = (hist_ts.groupby(['location', 'modality'])
                   .agg({'duration_per_exam': 'mean', 'num_rooms': 'max'})  # Mean per-exam duration
                   .reset_index())
    capacity_df['max_duration_capacity'] = capacity_df['duration_per_exam'] * capacity_df['num_rooms'] * 24  # Total daily capacity (assuming 24 exams/day max)
    capacity_df = capacity_df[['location', 'modality', 'num_rooms', 'max_duration_capacity']]
    print("\nCalculated Daily Historical Duration Capacities (minutes):")
    print(capacity_df)
    
    dow_effects = hist_df.assign(day_of_week=hist_df['date'].dt.dayofweek).groupby('day_of_week')['exam_count'].mean().to_dict()
    print("\nDay-of-Week Effects (Average Daily Exams):")
    for dow, avg in dow_effects.items():
        print(f"Day {dow} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]}): {avg:.2f}")
    
    scheduled_df = None
    if scheduled_csv and os.path.exists(scheduled_csv):
        scheduled_df = pd.read_csv(scheduled_csv, parse_dates=['date'])
        scheduled_columns = {'date', 'location', 'modality', 'scheduled_count', 'procedure_duration', 'num_rooms'}
        if not scheduled_columns.issubset(scheduled_df.columns):
            missing = scheduled_columns - set(scheduled_df.columns)
            raise ValueError(f"Scheduled CSV missing required columns: {missing}")
        scheduled_df['procedure_duration'] = pd.to_numeric(scheduled_df['procedure_duration'], errors='coerce')
    
    budget_df = None
    if budget_csv and os.path.exists(budget_csv):
        budget_df = pd.read_csv(budget_csv)
        budget_columns = {'location', 'modality', 'budget_count'}
        if not budget_columns.issubset(budget_df.columns):
            missing = budget_columns - set(budget_df.columns)
            raise ValueError(f"Budget CSV missing required columns: {missing}")
    
    return hist_ts, scheduled_df, budget_df, capacity_df, dow_effects

def train_prophet_model(args):
    """Train Prophet model with logistic growth"""
    ts_data, location, modality = args
    combo_data = ts_data[(ts_data['location'] == location) & (ts_data['modality'] == modality)]
    if len(combo_data) < 10:
        print(f"Skipping {location}, {modality}: <10 data points.")
        return (location, modality), (None, None)
    
    combo_ts = combo_data[['ds', 'y']]
    train_size = max(10, len(combo_ts) - 7)
    train = combo_ts.iloc[:train_size]
    
    try:
        holiday_df = pd.DataFrame({
            'holiday': 'us_holidays',
            'ds': pd.to_datetime(list(holidays.US(years=[2023, 2024, 2025]).keys())),
            'lower_window': 0,
            'upper_window': 0
        })
        
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            holidays=holiday_df,
            interval_width=0.95,
            growth='logistic',
            changepoint_prior_scale=0.1
        )
        train['cap'] = combo_data['y'].max() * 2
        model.fit(train)
        
        data_days = (train['ds'].max() - train['ds'].min()).days + 1
        unique_days = len(train['ds'].unique())
        print(f"Training {location}, {modality}: {unique_days} unique days, {len(train)} data points")
        
        if unique_days >= 15:
            initial_days = max(7, unique_days * 2 // 3)
            horizon_days = min(5, unique_days - initial_days)
            if horizon_days > 0:
                df_cv = cross_validation(model, initial=f'{initial_days} days', period='7 days', horizon=f'{horizon_days} days')
                df_metrics = performance_metrics(df_cv)
                print(f"\nMetrics for {location}, {modality}:\n{df_metrics[['horizon', 'mae']].to_string(index=False)}")
            else:
                print(f"Skipping CV for {location}, {modality}: Not enough days for horizon.")
        else:
            print(f"Skipping CV for {location}, {modality}: Too few unique days ({unique_days}).")
        
        return (location, modality), (model, train['ds'].max())
    except Exception as e:
        print(f"Error training {location}, {modality}: {e}")
        return (location, modality), (None, None)

def predict_combo(date, location, modality, scheduled_row, budget_df, capacity_df, model_info, hist_ts, dow_effects):
    """Predict with corrected duration logic"""
    model, last_train_date = model_info or (None, None)
    dow = date.dayofweek
    dow_factor = dow_effects.get(dow, 1.0) / max(dow_effects.values(), default=1.0)
    holiday = is_holiday_cached(date.strftime('%Y-%m-%d'))
    is_weekend = dow in [5, 6]
    
    capacity_row = capacity_df[(capacity_df['location'] == location) & (capacity_df['modality'] == modality)]
    max_duration_capacity = capacity_row['max_duration_capacity'].iloc[0] if not capacity_row.empty else float('inf')
    num_rooms = capacity_row['num_rooms'].iloc[0] if not capacity_row.empty else 1
    
    hist_combo = hist_ts[(hist_ts['location'] == location) & (hist_ts['modality'] == modality)]
    hist_avg_duration_per_exam = (hist_combo['procedure_duration'] / hist_combo['y']).mean() if not hist_combo.empty else 30
    hist_max_exams = int(hist_combo['y'].max()) * 3 if not hist_combo.empty else 100
    
    if scheduled_row is not None:
        scheduled_count = int(scheduled_row['scheduled_count'])
        total_scheduled_duration = scheduled_row['procedure_duration']
        is_scheduled = True
    else:
        scheduled_count = 0
        total_scheduled_duration = 0
        is_scheduled = False
    
    budget_count = (budget_df[(budget_df['location'] == location) & (budget_df['modality'] == modality)]
                    ['budget_count'].iloc[0] if budget_df is not None and not is_weekend and
                    not budget_df[(budget_df['location'] == location) & (budget_df['modality'] == modality)].empty else 0)
    
    if scheduled_count == 0 or holiday:
        pred_additional = 0
        total_predicted = scheduled_count if holiday else 0
        total_duration_predicted = total_scheduled_duration if holiday else 0
        yhat_lower, yhat_upper = (scheduled_count, scheduled_count) if holiday else (0, 0)
    elif model and last_train_date and (date - last_train_date).days > 0:
        future = pd.DataFrame({'ds': [date], 'cap': hist_max_exams})
        forecast = model.predict(future)
        pred_total_raw = max(0, int(round(forecast['yhat'].iloc[-1])))
        pred_total = min(pred_total_raw * dow_factor, hist_max_exams)
        pred_additional = max(0, pred_total - scheduled_count) if is_scheduled else pred_total
        yhat_lower = max(0, int(round(forecast['yhat_lower'].iloc[-1] * dow_factor)))
        yhat_upper = min(int(round(forecast['yhat_upper'].iloc[-1] * dow_factor)), hist_max_exams)
        
        print(f"{location}, {modality} on {date}: yhat={pred_total}, scheduled={scheduled_count}, initial_pred_additional={pred_additional}")
        
        remaining_duration = max(0, max_duration_capacity * 1.5 - total_scheduled_duration)
        max_additional_exams = int(remaining_duration / hist_avg_duration_per_exam)
        pred_additional = min(pred_additional, max_additional_exams)
        print(f"After capacity: pred_additional={pred_additional}, max_additional_exams={max_additional_exams}")
        
        total_predicted = scheduled_count + pred_additional
        total_duration_predicted = total_scheduled_duration + (pred_additional * hist_avg_duration_per_exam)
        
        if not is_scheduled and budget_count and total_duration_predicted > (budget_duration := budget_count * hist_avg_duration_per_exam * 1.1):
            excess_duration = total_duration_predicted - budget_duration
            pred_additional = max(0, pred_additional - int(excess_duration / hist_avg_duration_per_exam))
            total_predicted = pred_additional
            total_duration_predicted = pred_additional * hist_avg_duration_per_exam
            print(f"After budget: pred_additional={pred_additional}")
        
        if total_duration_predicted > max_duration_capacity * 1.5:
            excess_duration = total_duration_predicted - max_duration_capacity * 1.5
            pred_additional = max(0, pred_additional - int(excess_duration / hist_avg_duration_per_exam))
            total_predicted = scheduled_count + pred_additional
            total_duration_predicted = total_scheduled_duration + (pred_additional * hist_avg_duration_per_exam)
            print(f"After final capacity: pred_additional={pred_additional}")
    else:
        pred_additional = 0
        total_predicted = scheduled_count
        total_duration_predicted = total_scheduled_duration
        yhat_lower, yhat_upper = (scheduled_count, scheduled_count) if is_scheduled else (0, 0)
        print(f"{location}, {modality} on {date}: No prediction, pred_additional=0")
    
    if pred_additional > 0:
        print(f"Final {location}, {modality}: pred_additional={pred_additional}, total_predicted={total_predicted}")
        return {
            'date': date.strftime('%Y-%m-%d'),
            'location': location,
            'modality': modality,
            'scheduled_count': scheduled_count if is_scheduled else 0,  # Use 0 instead of 'N/A'
            'num_rooms': num_rooms,
            'predicted_additional': pred_additional,
            'max_duration_capacity': max_duration_capacity if max_duration_capacity != float('inf') else np.nan,  # Use np.nan
            'total_predicted': total_predicted,
            'total_duration_predicted': total_duration_predicted,
            'budget_count': budget_count if budget_count else 0,  # Use 0 instead of 'N/A'
            'variance': total_predicted - budget_count if budget_count else np.nan,  # Use np.nan
            'is_holiday': holiday,
            'yhat_lower': yhat_lower,
            'yhat_upper': yhat_upper
        }
    else:
        print(f"{location}, {modality} on {date}: Excluded, pred_additional={pred_additional}")
    return None


def predict_future_exams(models, start_date, days_ahead, scheduled_df, budget_df, capacity_df, dow_effects):
    """Predict exam counts with optimized logic"""
    if not models:
        print("No models trained. Cannot predict.")
        return pd.DataFrame(columns=['date', 'location', 'modality', 'scheduled_count', 'num_rooms',
                                     'predicted_additional', 'max_duration_capacity', 'total_predicted',
                                     'total_duration_predicted', 'budget_count', 'variance', 'is_holiday',
                                     'yhat_lower', 'yhat_upper'])
    
    start_date = pd.to_datetime(start_date)
    future_dates = pd.date_range(start=start_date, periods=days_ahead, freq='D')
    predictions = []
    
    for date in future_dates:
        scheduled_on_date = scheduled_df[scheduled_df['date'].dt.date == date.date()] if scheduled_df is not None else pd.DataFrame()
        scheduled_combos = set(scheduled_on_date.apply(lambda row: (row['location'], row['modality']), axis=1))
        
        for _, row in scheduled_on_date.iterrows():
            pred = predict_combo(date, row['location'], row['modality'], row, budget_df, capacity_df,
                                 models.get((row['location'], row['modality'])), hist_ts, dow_effects)
            if pred:
                predictions.append(pred)
        
        if budget_df is not None and not is_holiday_cached(date.strftime('%Y-%m-%d')) and date.dayofweek not in [5, 6]:
            for _, budget_row in budget_df.iterrows():
                loc_mod = (budget_row['location'], budget_row['modality'])
                if loc_mod not in scheduled_combos:
                    pred = predict_combo(date, *loc_mod, None, budget_df, capacity_df, models.get(loc_mod), hist_ts, dow_effects)
                    if pred:
                        predictions.append(pred)
    
    result = pd.DataFrame(predictions)
    print(f"Raw predictions count: {len(result)}")
    return result

def plot_predictions(predictions, hist_ts):
    """Optimized plotting"""
    if predictions.empty:
        print("No predictions to plot.")
        return
    
    plt.figure(figsize=(12, 6))
    for (loc, mod), group in predictions.groupby(['location', 'modality']):
        hist_group = hist_ts[(hist_ts['location'] == loc) & (hist_ts['modality'] == mod)]
        if not hist_group.empty:
            plt.plot(hist_group['ds'], hist_group['y'], label=f'{loc} {mod}', alpha=0.5)
        plt.plot(pd.to_datetime(group['date']), group['total_predicted'], label=f'{loc} {mod} Predicted', marker='o')
        plt.fill_between(pd.to_datetime(group['date']), group['yhat_lower'], group['yhat_upper'], alpha=0.2)
    plt.xlabel('Date')
    plt.ylabel('Exam Count')
    plt.title('Predicted Exam Counts (Additional Only)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('exam_predictions_plot.png', bbox_inches='tight')
    plt.close()
    print("Plot saved to 'exam_predictions_plot.png'")

def save_predictions(predictions, output_file):
    if predictions.empty:
        print("No predictions to save.")
        return
    
    predictions.to_csv(output_file, index=False)
    print(f"Predictions saved to '{output_file}'")
    
    # Convert all potentially problematic columns to numeric, coercing errors to NaN
    numeric_cols = ['scheduled_count', 'max_duration_capacity', 'budget_count', 'variance']
    for col in numeric_cols:
        predictions[col] = pd.to_numeric(predictions[col], errors='coerce')
    
    daily_summary = (predictions
                     .groupby('date')
                     .agg({'scheduled_count': 'sum', 'num_rooms': 'sum', 'total_predicted': 'sum',
                           'total_duration_predicted': 'sum', 'budget_count': 'sum',
                           'yhat_lower': 'sum', 'yhat_upper': 'sum'})
                     .reset_index()
                     .rename(columns={'scheduled_count': 'total_scheduled'}))
    daily_summary['variance'] = daily_summary['total_predicted'] - daily_summary['budget_count']
    
    # Handle NaN in output for readability
    daily_summary = daily_summary.fillna('N/A')
    
    print("\nDaily Summary:")
    print(daily_summary.to_string(index=False))
    
    summary_file = output_file.replace('.csv', '_summary.csv')
    daily_summary.to_csv(summary_file, index=False)
    print(f"Summary saved to '{summary_file}'")


if __name__ == "__main__":
    hist_df = pd.read_csv("exam_data.csv", parse_dates=['date'])
    dates = pd.date_range(start="2024-01-01", end="2025-03-18", freq="D")
    extended_hist = pd.concat([hist_df.assign(date=date,
                                              exam_count=hist_df['exam_count'] * (1 + np.random.uniform(-0.1, 0.1)),
                                              procedure_duration=hist_df['procedure_duration'] * (1 + np.random.uniform(-0.1, 0.1)))
                              for date in dates], ignore_index=True)
    extended_hist.to_csv("extended_exam_data.csv", index=False)

    historical_csv = "extended_exam_data.csv"
    scheduled_csv = "scheduled_exams.csv"
    budget_csv = "budget_exams.csv"
    
    try:
        hist_ts, scheduled_df, budget_df, capacity_df, dow_effects = load_and_prepare_data(historical_csv, scheduled_csv, budget_csv)
        
        combos = [(hist_ts, loc, mod) for loc, mod in hist_ts.groupby(['location', 'modality']).groups.keys()
                  if len(hist_ts[(hist_ts['location'] == loc) & (hist_ts['modality'] == mod)]) >= 10]
        print(f"Training {len(combos)} combos using {cpu_count()} cores...")
        with Pool(cpu_count()) as pool:
            models = dict(pool.map(train_prophet_model, combos))
        
        predictions = predict_future_exams(models, '2025-03-24', 7, scheduled_df, budget_df, capacity_df, dow_effects)
        print("\nPredicted Exam Counts:")
        if predictions.empty:
            print("No predictions with additional exams.")
        else:
            print(predictions.sort_values(by=['date', 'location', 'modality']))
        
        save_predictions(predictions, "exam_predictions.csv")
        plot_predictions(predictions, hist_ts)
    
    except Exception as e:
        print(f"Error: {e}")

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import os

def load_and_prepare_data(historical_csv, scheduled_csv=None, budget_csv=None):
    """Load and prepare data, including historical max exams, duration, and trends"""
    if not os.path.exists(historical_csv):
        raise FileNotFoundError(f"Historical CSV file '{historical_csv}' not found.")
    hist_df = pd.read_csv(historical_csv)
    
    required_columns = {'date', 'location', 'modality', 'exam_count', 'procedure_duration', 'num_rooms'}
    if not required_columns.issubset(hist_df.columns):
        missing = required_columns - set(hist_df.columns)
        raise ValueError(f"Historical CSV missing required columns: {missing}")
    
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    hist_df['day_of_week'] = hist_df['date'].dt.dayofweek
    hist_df['month'] = hist_df['date'].dt.month
    hist_df['day_of_year'] = hist_df['date'].dt.dayofyear
    hist_df['duration_per_exam'] = hist_df['procedure_duration'] / hist_df['exam_count']
    
    location_encoder = LabelEncoder()
    modality_encoder = LabelEncoder()
    hist_df['location_encoded'] = location_encoder.fit_transform(hist_df['location'])
    hist_df['modality_encoded'] = modality_encoder.fit_transform(hist_df['modality'])
    
    # Compute historical stats per combo
    historical_stats_df = hist_df.groupby(['location', 'modality', 'num_rooms']).agg({
        'exam_count': ['max', 'mean'],
        'procedure_duration': 'max',
        'duration_per_exam': 'mean'
    }).reset_index()
    historical_stats_df.columns = ['location', 'modality', 'num_rooms', 'historical_max_exams', 'historical_mean_exams', 'historical_max_duration', 'historical_duration_per_exam']
    # Calculate dynamic WORKDAY_MINUTES per combo
    historical_stats_df['workday_minutes'] = historical_stats_df.apply(
        lambda row: max(480, row['historical_max_duration'] / row['num_rooms']), axis=1
    )
    print("\nHistorical Stats (Max Exams, Mean Exams, Max Duration, Avg Duration per Exam, Workday Minutes):")
    print(historical_stats_df)
    
    dow_effects = hist_df.groupby('day_of_week')['exam_count'].mean().to_dict()
    print("\nDay-of-Week Effects (Average Exams):")
    for dow, avg in dow_effects.items():
        print(f"Day {dow} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]}): {avg:.2f}")
    
    scheduled_df = None
    if scheduled_csv and os.path.exists(scheduled_csv):
        scheduled_df = pd.read_csv(scheduled_csv)
        scheduled_columns = {'date', 'location', 'modality', 'scheduled_count', 'num_rooms', 'procedure_duration'}
        if not scheduled_columns.issubset(scheduled_df.columns):
            missing = scheduled_columns - set(scheduled_df.columns)
            raise ValueError(f"Scheduled CSV missing required columns: {missing}")
        scheduled_df['date'] = pd.to_datetime(scheduled_df['date'])
        scheduled_df['duration_per_exam'] = np.where(
            (scheduled_df['scheduled_count'] > 0) & (scheduled_df['procedure_duration'] >= 0),
            scheduled_df['procedure_duration'] / scheduled_df['scheduled_count'],
            15
        )
    else:
        raise ValueError("Scheduled exams CSV is required for this forecast.")
    
    budget_df = None
    if budget_csv and os.path.exists(budget_csv):
        budget_df = pd.read_csv(budget_csv)
        budget_columns = {'location', 'modality', 'budget_count'}
        if not budget_columns.issubset(budget_df.columns):
            missing = budget_columns - set(budget_df.columns)
            raise ValueError(f"Budget CSV missing required columns: {missing}")
    
    return hist_df, scheduled_df, budget_df, dow_effects, location_encoder, modality_encoder, historical_stats_df

def train_and_evaluate_model(df, model_type='random_forest'):
    features = ['day_of_week', 'month', 'day_of_year', 'location_encoded', 'modality_encoded', 'num_rooms', 'duration_per_exam']
    X = df[features]
    y = df['exam_count']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_mse = mean_squared_error(y_train, y_train_pred)
    test_mse = mean_squared_error(y_test, y_test_pred)
    
    print(f"\nRandom Forest Model Performance:")
    print(f"Training R²: {train_r2:.4f}")
    print(f"Test R²: {test_r2:.4f}")
    print(f"Training MAE: {train_mae:.4f}")
    print(f"Test MAE: {test_mae:.4f}")
    print(f"Training MSE: {train_mse:.4f}")
    print(f"Test MSE: {test_mse:.4f}")
    
    return model, features

def is_holiday(date, holidays):
    return date.strftime('%Y-%m-%d') in holidays

def predict_future_exams(model, start_date, days_ahead, scheduled_df, budget_df, historical_stats_df,
                        dow_effects, location_encoder, modality_encoder, feature_names):
    if scheduled_df is None or scheduled_df.empty:
        print("No scheduled exams to predict.")
        return pd.DataFrame(columns=['date', 'location', 'modality', 'scheduled_count',
                                    'predicted_additional', 'max_capacity', 'total_predicted',
                                    'budget_count', 'variance', 'is_holiday'])
    
    start_date = pd.to_datetime(start_date)
    future_dates = [start_date + timedelta(days=i) for i in range(days_ahead)]
    
    holidays = {'2025-01-01', '2025-05-26', '2025-07-04', '2025-09-01', '2025-11-27', '2025-12-25'}
    
    predictions = []
    for date in future_dates:
        day_scheduled = scheduled_df[scheduled_df['date'] == date]
        dow = date.dayofweek
        dow_factor = dow_effects.get(dow, 1.0) / max(dow_effects.values()) if dow_effects else 1.0
        holiday = is_holiday(date, holidays)
        is_weekend = dow in [5, 6]
        
        if not day_scheduled.empty:
            for _, row in day_scheduled.iterrows():
                location = row['location']
                modality = row['modality']
                scheduled_count = row['scheduled_count']
                num_rooms = row['num_rooms']
                procedure_duration = row['procedure_duration']
                duration_per_exam = row['duration_per_exam']
                
                try:
                    loc_encoded = location_encoder.transform([location])[0]
                    mod_encoded = modality_encoder.transform([modality])[0]
                except ValueError:
                    print(f"Warning: '{location}' or '{modality}' not in training data. Skipping.")
                    continue
                
                # Get historical stats for this combo
                hist_stats_row = historical_stats_df[(historical_stats_df['location'] == location) &
                                                    (historical_stats_df['modality'] == modality) &
                                                    (historical_stats_df['num_rooms'] == num_rooms)]
                if hist_stats_row.empty:
                    print(f"Warning: No historical data for {location}, {modality}, {num_rooms} rooms. Using scheduled data only.")
                    historical_max_exams = float('inf')
                    historical_mean_exams = scheduled_count
                    historical_max_duration = 480 * num_rooms  # Default fallback
                    hist_duration_per_exam = duration_per_exam
                    workday_minutes = 480
                else:
                    historical_max_exams = hist_stats_row['historical_max_exams'].iloc[0]
                    historical_mean_exams = hist_stats_row['historical_mean_exams'].iloc[0]
                    historical_max_duration = hist_stats_row['historical_max_duration'].iloc[0]
                    hist_duration_per_exam = hist_stats_row['historical_duration_per_exam'].iloc[0]
                    workday_minutes = hist_stats_row['workday_minutes'].iloc[0]
                
                # Calculate max capacity based on scheduled data (for reference)
                max_capacity_time = int((workday_minutes * num_rooms) / duration_per_exam) if duration_per_exam > 0 else 0
                max_capacity = min(max_capacity_time, historical_max_exams) if historical_max_exams != float('inf') else max_capacity_time
                
                # Max exams within workday minutes and historical max duration
                max_exams_workday = int((workday_minutes * num_rooms) / hist_duration_per_exam) if hist_duration_per_exam > 0 else 0
                max_exams_by_duration = int(historical_max_duration / hist_duration_per_exam) if hist_duration_per_exam > 0 and historical_max_duration != float('inf') else max_exams_workday
                overall_max_exams = min(max_exams_workday, max_exams_by_duration, historical_max_exams) if historical_max_exams != float('inf') else max_exams_workday
                
                # Predict additional exams with historical trend influence
                features = pd.DataFrame([[date.dayofweek, date.month, date.dayofyear, loc_encoded, mod_encoded, num_rooms, duration_per_exam]],
                                      columns=feature_names)
                pred_additional_raw = max(0, int(round(model.predict(features)[0])))
                pred_additional_raw = min(pred_additional_raw, int(historical_mean_exams * dow_factor))  # Cap by historical mean
                pred_additional = int(pred_additional_raw * dow_factor)
                
                # Scale prediction to trend with historical mean
                historical_trend_factor = historical_mean_exams / historical_max_exams if historical_max_exams != float('inf') and historical_max_exams > 0 else 1.0
                pred_additional = int(pred_additional * historical_trend_factor)  # No hard capacity cap here
                
                # Budget data (for variance only)
                budget_count = None
                if budget_df is not None and not is_weekend:
                    budget_row = budget_df[(budget_df['location'] == location) & (budget_df['modality'] == modality)]
                    budget_count = budget_row['budget_count'].iloc[0] if not budget_row.empty else None
                else:
                    budget_count = 0
                
                # Total predicted, constrained by duration only
                if scheduled_count == 0:
                    total_predicted = 0
                elif holiday:
                    total_predicted = scheduled_count
                else:
                    total_unconstrained = scheduled_count + pred_additional
                    total_duration = total_unconstrained * hist_duration_per_exam
                    max_duration = min(workday_minutes * num_rooms, historical_max_duration if historical_max_duration != float('inf') else float('inf'))
                    if total_duration > max_duration and max_duration != float('inf'):
                        total_predicted = min(total_unconstrained, int(max_duration / hist_duration_per_exam))
                    else:
                        total_predicted = total_unconstrained
                
                variance = total_predicted - budget_count if budget_count is not None else None
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'), 'location': location, 'modality': modality,
                    'scheduled_count': scheduled_count, 'predicted_additional': pred_additional,
                    'max_capacity': max_capacity, 'total_predicted': total_predicted,
                    'budget_count': budget_count if budget_count is not None else 'N/A',
                    'variance': variance if variance is not None else 'N/A', 'is_holiday': holiday
                })
    
    return pd.DataFrame(predictions)

def print_daily_summary(predictions):
    if predictions.empty:
        print("No predictions to summarize.")
        return
    
    predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
    daily_summary = predictions.groupby('date').agg({
        'scheduled_count_numeric': 'sum', 'total_predicted': 'sum',
        'budget_count': lambda x: x.sum() if x.notna().any() else np.nan
    }).reset_index()
    daily_summary['variance'] = daily_summary['total_predicted'] - daily_summary['budget_count']
    daily_summary = daily_summary.rename(columns={'scheduled_count_numeric': 'total_scheduled'})
    
    print("\nDaily Summary of Total Scheduled, Predicted Exams vs Budget:")
    print(daily_summary.to_string(index=False))

def save_predictions(predictions, output_file):
    predictions.to_csv(output_file, index=False)
    print(f"Predictions saved to '{output_file}'")
    
    if not predictions.empty:
        predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
        daily_summary = predictions.groupby('date').agg({
            'scheduled_count_numeric': 'sum', 'total_predicted': 'sum',
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
        hist_df, scheduled_df, budget_df, dow_effects, location_encoder, modality_encoder, historical_stats_df = load_and_prepare_data(
            historical_csv, scheduled_csv, budget_csv
        )
        
        rf_model, feature_names = train_and_evaluate_model(hist_df, model_type='random_forest')
        
        start_date = '2025-03-24'
        days_ahead = 7
        
        predictions = predict_future_exams(
            rf_model, start_date, days_ahead, scheduled_df, budget_df, historical_stats_df,
            dow_effects, location_encoder, modality_encoder, feature_names
        )
        
        print("\nPredicted Exam Counts (Random Forest with Scheduled Capacity):")
        print(predictions.sort_values(by=['date', 'location', 'modality']))
        
        print_daily_summary(predictions)
        save_predictions(predictions, "exam_predictions_rf_scheduled.csv")
    
    except Exception as e:
        print(f"Error: {e}")


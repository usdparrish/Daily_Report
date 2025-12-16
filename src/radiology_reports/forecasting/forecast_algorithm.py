import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import os

def load_and_prepare_data(historical_csv, scheduled_csv=None, budget_csv=None):
    """Load and prepare data, calculate capacity and day-of-week effects"""
    if not os.path.exists(historical_csv):
        raise FileNotFoundError(f"Historical CSV file '{historical_csv}' not found.")
    hist_df = pd.read_csv(historical_csv)
    required_columns = {'date', 'location', 'modality', 'exam_count'}
    if not required_columns.issubset(hist_df.columns):
        missing = required_columns - set(hist_df.columns)
        raise ValueError(f"Historical CSV missing required columns: {missing}")
    
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    hist_df['day_of_week'] = hist_df['date'].dt.dayofweek
    hist_df['month'] = hist_df['date'].dt.month
    hist_df['day_of_year'] = hist_df['date'].dt.dayofyear
    
    location_encoder = LabelEncoder()
    modality_encoder = LabelEncoder()
    hist_df['location_encoded'] = location_encoder.fit_transform(hist_df['location'])
    hist_df['modality_encoded'] = modality_encoder.fit_transform(hist_df['modality'])
    
    # Calculate historical capacity
    capacity_df = hist_df.groupby(['location', 'modality'])['exam_count'].max().reset_index()
    capacity_df = capacity_df.rename(columns={'exam_count': 'max_capacity'})
    print("\nCalculated Historical Capacities:")
    print(capacity_df)
    
    # Calculate day-of-week effects
    dow_effects = hist_df.groupby('day_of_week')['exam_count'].mean().to_dict()
    print("\nDay-of-Week Effects (Average Exams):")
    for dow, avg in dow_effects.items():
        print(f"Day {dow} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]}): {avg:.2f}")
    
    # Load scheduled data (optional)
    scheduled_df = None
    if scheduled_csv and os.path.exists(scheduled_csv):
        scheduled_df = pd.read_csv(scheduled_csv)
        scheduled_columns = {'date', 'location', 'modality', 'scheduled_count'}
        if not scheduled_columns.issubset(scheduled_df.columns):
            missing = scheduled_columns - set(scheduled_df.columns)
            raise ValueError(f"Scheduled CSV missing required columns: {missing}")
        scheduled_df['date'] = pd.to_datetime(scheduled_df['date'])
    else:
        print("Warning: No scheduled exams CSV provided. Predictions will be empty for non-budgeted combos.")
    
    # Load budget data (optional, no date column)
    budget_df = None
    if budget_csv and os.path.exists(budget_csv):
        budget_df = pd.read_csv(budget_csv)
        budget_columns = {'location', 'modality', 'budget_count'}
        if not budget_columns.issubset(budget_df.columns):
            missing = budget_columns - set(budget_df.columns)
            raise ValueError(f"Budget CSV missing required columns: {missing}")
    
    return hist_df, scheduled_df, budget_df, capacity_df, dow_effects, location_encoder, modality_encoder

def train_and_evaluate_model(df, model_type='linear'):
    """Train and evaluate a model, returning performance metrics"""
    features = ['day_of_week', 'month', 'day_of_year', 'location_encoded', 'modality_encoded']
    X = df[features]
    y = df['exam_count']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    if model_type == 'linear':
        model = LinearRegression()
    elif model_type == 'random_forest':
        model = RandomForestRegressor(n_estimators=100, random_state=42)
    else:
        raise ValueError("Unsupported model_type. Use 'linear' or 'random_forest'.")
    
    model.fit(X_train, y_train)
    
    # Predictions
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Metrics
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_mse = mean_squared_error(y_train, y_train_pred)
    test_mse = mean_squared_error(y_test, y_test_pred)
    
    print(f"\n{model_type.capitalize()} Model Performance:")
    print(f"Training R²: {train_r2:.4f}")
    print(f"Test R²: {test_r2:.4f}")
    print(f"Training MAE: {train_mae:.4f}")
    print(f"Test MAE: {test_mae:.4f}")
    print(f"Training MSE: {train_mse:.4f}")
    print(f"Test MSE: {test_mse:.4f}")
    
    return model, features

def is_holiday(date, holidays):
    """Check if a date is a holiday"""
    return date.strftime('%Y-%m-%d') in holidays

def predict_future_exams(model, start_date, days_ahead, scheduled_df, budget_df, capacity_df, 
                        dow_effects, location_encoder, modality_encoder, feature_names):
    """Predict exam counts, capping at 10% above budget"""
    if (scheduled_df is None or scheduled_df.empty) and (budget_df is None or budget_df.empty):
        print("No scheduled or budgeted exams to predict.")
        return pd.DataFrame(columns=['date', 'location', 'modality', 'scheduled_count', 
                                    'predicted_additional', 'max_capacity', 'total_predicted', 
                                    'budget_count', 'variance', 'is_holiday'])
    
    start_date = pd.to_datetime(start_date)
    future_dates = [start_date + timedelta(days=i) for i in range(days_ahead)]
    
    holidays = {
        '2025-01-01', # New Year's Day
        '2025-05-26', # Memorial Day
        '2025-07-04', # Independence Day
        '2025-09-01', # Labor Day
        '2025-11-27', # Thanksgiving Day
        '2025-12-25', # Christmas Day
    }
    
    predictions = []
    for date in future_dates:
        day_scheduled = scheduled_df[scheduled_df['date'] == date] if scheduled_df is not None else pd.DataFrame()
        
        dow = date.dayofweek
        dow_factor = dow_effects.get(dow, 1.0) / max(dow_effects.values()) if dow_effects else 1.0
        holiday = is_holiday(date, holidays)
        is_weekend = dow in [5, 6]
        
        # Process scheduled combos first
        scheduled_combos = set()
        if not day_scheduled.empty:
            for _, row in day_scheduled.iterrows():
                location = row['location']
                modality = row['modality']
                scheduled_count = row['scheduled_count']
                scheduled_combos.add((location, modality))
                
                try:
                    loc_encoded = location_encoder.transform([location])[0]
                    mod_encoded = modality_encoder.transform([modality])[0]
                except ValueError:
                    print(f"Warning: '{location}' or '{modality}' not in training data. Skipping.")
                    continue
                
                features = pd.DataFrame([[
                    date.dayofweek,
                    date.month,
                    date.dayofyear,
                    loc_encoded,
                    mod_encoded
                ]], columns=feature_names)
                
                pred_additional_raw = max(0, int(round(model.predict(features)[0])))
                pred_additional = int(pred_additional_raw * dow_factor)
                
                # Historical capacity
                capacity_row = capacity_df[
                    (capacity_df['location'] == location) & 
                    (capacity_df['modality'] == modality)
                ]
                max_capacity = capacity_row['max_capacity'].iloc[0] if not capacity_row.empty else float('inf')
                
                # Budget (0 on weekends)
                budget_count = None
                if budget_df is not None and not is_weekend:
                    budget_row = budget_df[
                        (budget_df['location'] == location) & 
                        (budget_df['modality'] == modality)
                    ]
                    budget_count = budget_row['budget_count'].iloc[0] if not budget_row.empty else None
                else:
                    budget_count = 0
                
                # Prediction logic
                if scheduled_count == 0:
                    total_predicted = 0
                elif holiday:
                    total_predicted = scheduled_count
                else:
                    total_unconstrained = scheduled_count + pred_additional
                    if budget_count is not None:
                        total_predicted = min(total_unconstrained, max_capacity, int(budget_count * 1.1))
                    else:
                        total_predicted = min(total_unconstrained, max_capacity)
                
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
        
        # Process budgeted but unscheduled combos (only on weekdays, not holidays)
        if budget_df is not None and not holiday and not is_weekend:
            for _, budget_row in budget_df.iterrows():
                location = budget_row['location']
                modality = budget_row['modality']
                if (location, modality) in scheduled_combos:
                    continue
                
                try:
                    loc_encoded = location_encoder.transform([location])[0]
                    mod_encoded = modality_encoder.transform([modality])[0]
                except ValueError:
                    print(f"Warning: '{location}' or '{modality}' not in training data. Skipping.")
                    continue
                
                features = pd.DataFrame([[
                    date.dayofweek,
                    date.month,
                    date.dayofyear,
                    loc_encoded,
                    mod_encoded
                ]], columns=feature_names)
                
                pred_additional_raw = max(0, int(round(model.predict(features)[0])))
                pred_additional = int(pred_additional_raw * dow_factor)
                
                # Historical capacity
                capacity_row = capacity_df[
                    (capacity_df['location'] == location) & 
                    (capacity_df['modality'] == modality)
                ]
                max_capacity = capacity_row['max_capacity'].iloc[0] if not capacity_row.empty else float('inf')
                
                budget_count = budget_row['budget_count']
                
                # Ensure some volume, capped at max_capacity and 10% above budget
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
    print(predictions)
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
        hist_df, scheduled_df, budget_df, capacity_df, dow_effects, location_encoder, modality_encoder = load_and_prepare_data(
            historical_csv, scheduled_csv, budget_csv
        )
        
        # Evaluate Linear Regression
        linear_model, feature_names = train_and_evaluate_model(hist_df, model_type='linear')
        
        # Evaluate Random Forest (optional comparison)
        rf_model, _ = train_and_evaluate_model(hist_df, model_type='random_forest')
        
        # Use Linear Regression for predictions (can switch to rf_model if preferred)
        model = linear_model
        
        start_date = '2025-05-03'
        days_ahead = 7
        
        predictions = predict_future_exams(
            model, 
            start_date, 
            days_ahead, 
            scheduled_df,
            budget_df,
            capacity_df,
            dow_effects,
            location_encoder, 
            modality_encoder, 
            feature_names
        )
        
        print("\nPredicted Exam Counts:")
        print(predictions.sort_values(by=['date', 'location', 'modality']))
        
        print_daily_summary(predictions)
        save_predictions(predictions, "exam_predictions.csv")
    
    except Exception as e:
        print(f"Error: {e}")

# Example CSV formats:
# exam_data.csv (historical):
"""
date,location,modality,exam_count
2024-01-15,Clinic A,MRI,5 # Monday, January
2024-01-16,Clinic B,X-Ray,3 # Tuesday, January
2024-01-17,Clinic A,MRI,6 # Wednesday, January
2024-01-18,Clinic B,CT,4 # Thursday, January
2024-03-01,Clinic A,MRI,4 # Friday, March
"""

# scheduled_exams.csv (current schedules):
"""
date,location,modality,scheduled_count
2025-03-01,Clinic A,MRI,2 # Saturday
2025-03-02,Clinic B,CT,0 # Sunday
2025-03-03,Clinic B,X-Ray,3 # Monday
"""

# budget_exams.csv (budgeted exams):
"""
location,modality,budget_count
Clinic A,MRI,3
Clinic B,CT,2
Clinic B,X-Ray,4
"""


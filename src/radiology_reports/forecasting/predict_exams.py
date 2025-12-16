import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import os

def load_and_prepare_data(historical_csv, scheduled_csv):
    if not os.path.exists(historical_csv):
        raise FileNotFoundError(f"Historical CSV file '{historical_csv}' not found.")
    hist_df = pd.read_csv(historical_csv)
    required_columns = {'date', 'location', 'modality', 'exam_count'}
    if not required_columns.issubset(hist_df.columns):
        missing = required_columns - set(hist_df.columns)
        raise ValueError(f"Historical CSV missing required columns: {missing}")
    hist_df['date'] = pd.to_datetime(hist_df['date'])

    if not os.path.exists(scheduled_csv):
        raise FileNotFoundError(f"Scheduled CSV file '{scheduled_csv}' not found.")
    scheduled_df = pd.read_csv(scheduled_csv, parse_dates=['date', 'inserted'])
    scheduled_columns = {'date', 'location', 'modality', 'scheduled_count', 'inserted'}
    if not scheduled_columns.issubset(scheduled_df.columns):
        missing = scheduled_columns - set(scheduled_df.columns)
        raise ValueError(f"Scheduled CSV missing required columns: {missing}")

    # Filter to data up to current date
    current_date = pd.to_datetime('2025-05-03')
    scheduled_df = scheduled_df[scheduled_df['inserted'] <= current_date].copy()

    # Get the most recent scheduled_count for each date, location, modality
    scheduled_df = scheduled_df.sort_values('inserted', ascending=False)  # Latest inserted first
    scheduled_agg_df = scheduled_df.groupby(['date', 'location', 'modality']).first().reset_index()
    # 'first()' takes the top row (most recent inserted) after sorting

    # Recalculate scheduling features based on the latest count
    scheduled_agg_df['days_ahead'] = (scheduled_agg_df['date'] - scheduled_agg_df['inserted']).dt.days
    scheduled_agg_df['scheduled_0_7_days'] = scheduled_agg_df.apply(
        lambda row: row['scheduled_count'] if row['days_ahead'] <= 7 else 0, axis=1)
    scheduled_agg_df['scheduled_8_14_days'] = scheduled_agg_df.apply(
        lambda row: row['scheduled_count'] if 8 <= row['days_ahead'] <= 14 else 0, axis=1)
    scheduled_agg_df['scheduled_15_plus_days'] = scheduled_agg_df.apply(
        lambda row: row['scheduled_count'] if row['days_ahead'] > 14 else 0, axis=1)

    # Merge with historical data for training
    train_df = pd.merge(hist_df, scheduled_agg_df, on=['date', 'location', 'modality'], how='left')
    train_df[['scheduled_count', 'scheduled_0_7_days', 'scheduled_8_14_days', 'scheduled_15_plus_days', 'days_ahead']] = \
        train_df[['scheduled_count', 'scheduled_0_7_days', 'scheduled_8_14_days', 'scheduled_15_plus_days', 'days_ahead']].fillna(0)
    
    train_df['day_of_week'] = train_df['date'].dt.dayofweek
    train_df['month'] = train_df['date'].dt.month
    train_df['day_of_year'] = train_df['date'].dt.dayofyear

    location_encoder = LabelEncoder()
    modality_encoder = LabelEncoder()
    train_df['location_encoded'] = location_encoder.fit_transform(train_df['location'])
    train_df['modality_encoded'] = modality_encoder.fit_transform(train_df['modality'])

    combo_stats_df = train_df.groupby(['location', 'modality']).agg({
        'exam_count': ['max', 'mean'],
        'scheduled_count': ['max', 'mean']
    }).reset_index()
    combo_stats_df.columns = ['location', 'modality', 'historical_max_exams', 'historical_mean_exams', 
                             'scheduled_max', 'scheduled_mean']

    print("\nHistorical and Scheduled Stats (Max Exams, Mean Exams, Max Scheduled, Mean Scheduled):")
    print(combo_stats_df)

    dow_effects = train_df.groupby('day_of_week')['exam_count'].mean().to_dict()
    print("\nDay-of-Week Effects (Average Exams, for reference only):")
    for dow, avg in dow_effects.items():
        print(f"Day {dow} ({['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dow]}): {avg:.2f}")

    # Prepare scheduled_df for prediction with latest counts
    scheduled_df = scheduled_agg_df.copy()
    scheduled_df['location_encoded'] = location_encoder.transform(scheduled_df['location'])
    scheduled_df['modality_encoded'] = modality_encoder.transform(scheduled_df['modality'])

    # Debug: Show scheduled data
    print("\nScheduled Data for Prediction (Latest Counts):")
    print(scheduled_df[['date', 'location', 'modality', 'scheduled_count', 'inserted']].head())

    return train_df, scheduled_df, dow_effects, location_encoder, modality_encoder, combo_stats_df

def train_and_evaluate_model(df, model_type='random_forest'):
    features = ['day_of_week', 'month', 'day_of_year', 'location_encoded', 'modality_encoded',
                'scheduled_count', 'scheduled_0_7_days', 'scheduled_8_14_days', 'scheduled_15_plus_days', 'days_ahead']
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

def predict_future_exams(model, start_date, days_ahead, scheduled_df, historical_stats_df,
                        dow_effects, location_encoder, modality_encoder, feature_names):
    if scheduled_df is None or scheduled_df.empty:
        print("No scheduled exams to predict.")
        return pd.DataFrame(columns=['date', 'location', 'modality', 'scheduled_count',
                                    'predicted_additional', 'total_predicted', 'is_holiday',
                                    'days_ahead', 'scheduled_0_7_days', 'scheduled_8_14_days', 
                                    'scheduled_15_plus_days'])

    start_date = pd.to_datetime(start_date)
    future_dates = [start_date + timedelta(days=i) for i in range(days_ahead)]
    current_date = pd.to_datetime('2025-05-03')
    holidays = {'2025-01-01', '2025-05-26', '2025-07-04', '2025-09-01', '2025-11-27', '2025-12-25'}

    predictions = []
    for date in future_dates:
        day_scheduled = scheduled_df[scheduled_df['date'] == date].copy()
        if not day_scheduled.empty:
            dow = date.dayofweek
            holiday = is_holiday(date, holidays)
            days_ahead_value = (date - current_date).days if date > current_date else day_scheduled['days_ahead'].iloc[0]

            for _, row in day_scheduled.iterrows():
                location = row['location']
                modality = row['modality']
                scheduled_count = row['scheduled_count']
                scheduled_0_7_days = row['scheduled_0_7_days']
                scheduled_8_14_days = row['scheduled_8_14_days']
                scheduled_15_plus_days = row['scheduled_15_plus_days']
                loc_encoded = row['location_encoded']
                mod_encoded = row['modality_encoded']

                features = pd.DataFrame([[dow, date.month, date.dayofyear, loc_encoded, mod_encoded,
                                        scheduled_count, scheduled_0_7_days, scheduled_8_14_days, 
                                        scheduled_15_plus_days, days_ahead_value]],
                                      columns=feature_names)

                total_predicted_raw = model.predict(features)[0]
                total_predicted = max(scheduled_count, int(round(total_predicted_raw)))
                predicted_additional = max(0, total_predicted - scheduled_count)

                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'location': location,
                    'modality': modality,
                    'scheduled_count': scheduled_count,
                    'predicted_additional': predicted_additional,
                    'total_predicted': total_predicted,
                    'is_holiday': holiday,
                    'days_ahead': days_ahead_value,
                    'scheduled_0_7_days': scheduled_0_7_days,
                    'scheduled_8_14_days': scheduled_8_14_days,
                    'scheduled_15_plus_days': scheduled_15_plus_days
                })
        else:
            # Optional: Predict without scheduled data if desired
            pass  # Add logic here if you want predictions without scheduled data

    predictions_df = pd.DataFrame(predictions)
    if not predictions_df.empty:
        predictions_df['date'] = predictions_df['date'].astype(str)
    return predictions_df

def print_daily_summary(predictions):
    if predictions.empty:
        print("No predictions to summarize.")
        return

    predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
    daily_summary = predictions.groupby('date').agg({
        'scheduled_count_numeric': 'sum',
        'total_predicted': 'sum'
    }).reset_index()
    daily_summary = daily_summary.rename(columns={'scheduled_count_numeric': 'total_scheduled'})

    print("\nDaily Summary of Total Scheduled and Predicted Exams:")
    print(daily_summary.to_string(index=False))

def save_predictions(predictions, output_file):
    predictions.to_csv(output_file, index=False)
    print(f"Predictions saved to '{output_file}'")

    if not predictions.empty:
        predictions['scheduled_count_numeric'] = pd.to_numeric(predictions['scheduled_count'], errors='coerce').fillna(0)
        daily_summary = predictions.groupby('date').agg({
            'scheduled_count_numeric': 'sum',
            'total_predicted': 'sum'
        }).reset_index()
        daily_summary = daily_summary.rename(columns={'scheduled_count_numeric': 'total_scheduled'})
        summary_file = output_file.replace('.csv', '_daily_summary.csv')
        daily_summary.to_csv(summary_file, index=False)
        print(f"Daily summary saved to '{summary_file}'")

if __name__ == "__main__":
    historical_csv = "exam_data.csv"
    scheduled_csv = "scheduled_exams.csv"

    try:
        train_df, scheduled_df, dow_effects, location_encoder, modality_encoder, historical_stats_df = load_and_prepare_data(
            historical_csv, scheduled_csv
        )

        rf_model, feature_names = train_and_evaluate_model(train_df, model_type='random_forest')

        start_date = '2025-05-03'
        days_ahead = 7

        predictions = predict_future_exams(
            rf_model, start_date, days_ahead, scheduled_df, historical_stats_df,
            dow_effects, location_encoder, modality_encoder, feature_names
        )

        print("\nPredicted Exam Counts (Random Forest with Scheduled Data):")
        print("Raw predictions:")
        print(predictions.head())
        sorted_predictions = predictions.sort_values(by=['date', 'location', 'modality'])
        print("Sorted predictions:")
        print(sorted_predictions[['date', 'location', 'modality', 'scheduled_count', 
                                  'predicted_additional', 'total_predicted', 'days_ahead', 
                                  'scheduled_0_7_days', 'scheduled_8_14_days', 'scheduled_15_plus_days']])

        print_daily_summary(predictions)
        save_predictions(predictions, "exam_predictions_rf_scheduled.csv")

    except Exception as e:
        print(f"Error: {e}")


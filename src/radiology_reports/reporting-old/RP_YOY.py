import pandas as pd

# Define file paths (replace with your actual file paths)
current_file = 'current_2025.csv'  # Your 2025 data file
last_year_file = 'last_year_2024.csv'  # Your 2024 data file (assumed same structure)

# Load both datasets
df_current = pd.read_csv(current_file)
df_last = pd.read_csv(last_year_file)

# Ensure required fields are present
required_cols = ['Patient Procedure Accession Number', 'Visit Referring Physician ID', 'Visit Referring Physician Location ID', 'Visit Referring Full Name', 'Visit Referring Practice', 'Visit Referring Practice Address']
for df in [df_current, df_last]:
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in data: {missing}")

# Add a year column for distinction
df_current['Year'] = 2025
df_last['Year'] = 2024

# Combine both for consistent extraction (if needed)
df_all = pd.concat([df_current, df_last], ignore_index=True)

# Extract unique Name, Practice, and Address per RP ID and Location ID (using first occurrence)
name_practice_address = df_all.groupby(['Visit Referring Physician ID', 'Visit Referring Physician Location ID']).agg({
    'Visit Referring Full Name': 'first',
    'Visit Referring Practice': 'first',
    'Visit Referring Practice Address': 'first'
}).reset_index()

# Compute number of procedures (count of unique Accession Numbers) for current year
agg_current = df_current.groupby(['Visit Referring Physician ID', 'Visit Referring Physician Location ID'])['Patient Procedure Accession Number'].nunique().reset_index(name='Procedures 2025')

# Same for last year
agg_last = df_last.groupby(['Visit Referring Physician ID', 'Visit Referring Physician Location ID'])['Patient Procedure Accession Number'].nunique().reset_index(name='Procedures 2024')

# Merge aggregations for comparison (outer join to include all)
comparison = pd.merge(agg_last, agg_current, on=['Visit Referring Physician ID', 'Visit Referring Physician Location ID'], how='outer').fillna(0)

# Calculate YoY changes
comparison['YoY Change'] = comparison['Procedures 2025'] - comparison['Procedures 2024']
comparison['YoY % Change'] = (comparison['YoY Change'] / comparison['Procedures 2024'].replace(0, float('nan'))) * 100  # NaN for div by zero

# Merge in Name, Practice, and Address
comparison = pd.merge(comparison, name_practice_address, on=['Visit Referring Physician ID', 'Visit Referring Physician Location ID'], how='left')

# Reorder columns for output
comparison = comparison[['Visit Referring Physician ID', 'Visit Referring Physician Location ID', 'Visit Referring Full Name', 'Visit Referring Practice', 'Visit Referring Practice Address', 'Procedures 2024', 'Procedures 2025', 'YoY Change', 'YoY % Change']]

# Output the full comparison to console (sample)
print("Sample YoY Procedure Comparison:")
print(comparison.head(10))

# Save full comparison to CSV
comparison.to_csv('yoy_procedure_comparison.csv', index=False)
print("\nFull YoY procedure comparison saved to 'yoy_procedure_comparison.csv'")

# Get top 25 negative trends (most negative YoY Change first, excluding zero/positive)
negative_trends = comparison[comparison['YoY Change'] < 0].sort_values('YoY Change', ascending=True).head(25)

# Output top 25 negative trends to console
print("\nTop 25 Negative YoY Trends (by Procedure Count):")
print(negative_trends)

# Save top 25 negative trends to CSV
negative_trends.to_csv('top_25_negative_procedure_trends.csv', index=False)
print("\nTop 25 negative procedure trends saved to 'top_25_negative_procedure_trends.csv'")

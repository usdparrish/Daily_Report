import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# Define file paths (replace with your actual file paths)
current_file = 'current_2025.csv'  # Your 2025 data file
last_year_file = 'last_year_2024.csv'  # Your 2024 data file (assumed same structure)

# Load both datasets
df_current = pd.read_csv(current_file)
df_last = pd.read_csv(last_year_file)

# Parse dates and extract month/year for analysis
df_current['Patient Procedure Schedule Start Date'] = pd.to_datetime(df_current['Patient Procedure Schedule Start Date'])
df_current['Month'] = df_current['Patient Procedure Schedule Start Date'].dt.month
df_current['Year'] = 2025

df_last['Patient Procedure Schedule Start Date'] = pd.to_datetime(df_last['Patient Procedure Schedule Start Date'])
df_last['Month'] = df_last['Patient Procedure Schedule Start Date'].dt.month
df_last['Year'] = 2024

# Ensure required fields are present (removed geo/demo fields from check)
required_cols = ['Patient Procedure Accession Number', 'Patient Procedure Jacket No', 'Visit Referring Physician ID', 
                 'Visit Referring Physician Location ID', 'Visit Referring Full Name', 'Visit Referring Practice', 
                 'Visit Referring Practice Address', 'Procedure Category Description', 'Procedure Location Name', 
                 'Procedure Code Description']
for df in [df_current, df_last]:
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in data: {missing}")

# ------------------- YoY Procedure Comparison (Procedures = count of unique Accession Numbers) -------------------
# Combine for consistent metadata extraction
df_all = pd.concat([df_current, df_last], ignore_index=True)

# Extract unique Name, Practice, and Address per RP ID and Location ID
metadata = df_all.groupby(['Visit Referring Physician ID', 'Visit Referring Physician Location ID']).agg({
    'Visit Referring Full Name': 'first',
    'Visit Referring Practice': 'first',
    'Visit Referring Practice Address': 'first'
}).reset_index()

# Compute procedures for current year
agg_current = df_current.groupby(['Visit Referring Physician ID', 'Visit Referring Physician Location ID'])['Patient Procedure Accession Number'].nunique().reset_index(name='Procedures 2025')

# Same for last year
agg_last = df_last.groupby(['Visit Referring Physician ID', 'Visit Referring Physician Location ID'])['Patient Procedure Accession Number'].nunique().reset_index(name='Procedures 2024')

# Merge and calculate YoY
comparison = pd.merge(agg_last, agg_current, on=['Visit Referring Physician ID', 'Visit Referring Physician Location ID'], how='outer').fillna(0)
comparison['YoY Change'] = comparison['Procedures 2025'] - comparison['Procedures 2024']
comparison['YoY % Change'] = (comparison['YoY Change'] / comparison['Procedures 2024'].replace(0, np.nan)) * 100
comparison = pd.merge(comparison, metadata, on=['Visit Referring Physician ID', 'Visit Referring Physician Location ID'], how='left')
comparison = comparison[['Visit Referring Physician ID', 'Visit Referring Physician Location ID', 'Visit Referring Full Name', 
                          'Visit Referring Practice', 'Visit Referring Practice Address', 'Procedures 2024', 'Procedures 2025', 
                          'YoY Change', 'YoY % Change']]

# Save full comparison
comparison.to_csv('yoy_procedure_comparison.csv', index=False)
print("Full YoY procedure comparison saved to 'yoy_procedure_comparison.csv'")

# Top 25 negative trends
negative_trends = comparison[comparison['YoY Change'] < 0].sort_values('YoY Change', ascending=True).head(25)
negative_trends.to_csv('top_25_negative_procedure_trends.csv', index=False)
print("Top 25 negative procedure trends saved to 'top_25_negative_procedure_trends.csv'")

# ------------------- Overall YTD Summary (2025 Focus) -------------------
total_referrals = len(df_current)  # Total procedures (rows)
unique_patients = df_current['Patient Procedure Jacket No'].nunique()
unique_rps = df_current['Visit Referring Physician ID'].nunique()
unique_practices = df_current['Visit Referring Practice'].nunique()
repeat_rate = (1 - (unique_patients / total_referrals)) * 100 if total_referrals > 0 else 0
avg_daily_volume = total_referrals / df_current['Patient Procedure Schedule Start Date'].dt.dayofyear.nunique()
mom_growth_avg = df_current.groupby('Month').size().pct_change().mean() * 100  # Approx MoM
top_modality = df_current['Procedure Category Description'].value_counts().idxmax()
top_modality_pct = (df_current['Procedure Category Description'].value_counts().max() / total_referrals) * 100
top_practice_pct = (df_current['Visit Referring Practice'].value_counts().max() / total_referrals) * 100

summary_data = {
    'Metric': ['Total Referrals', 'Unique Patients', 'Repeat Rate (%)', 'Unique RPs', 'Unique Practices', 
               'Average Daily Volume', 'Average MoM Growth (%)', 'Top Modality', 'Top Modality (%)', 
               'Top Practice Concentration (%)'],
    'Value': [total_referrals, unique_patients, round(repeat_rate, 1), unique_rps, unique_practices, 
              round(avg_daily_volume, 0), round(mom_growth_avg, 1), top_modality, round(top_modality_pct, 1), 
              round(top_practice_pct, 1)]
}
summary_df = pd.DataFrame(summary_data)
summary_df.to_csv('ytd_summary_2025.csv', index=False)
print("YTD Summary saved to 'ytd_summary_2025.csv'")
print(summary_df)

# ------------------- Monthly Trend Breakdown -------------------
monthly_current = df_current.groupby('Month').agg({'Patient Procedure Accession Number': 'count'}).reset_index()
monthly_current.columns = ['Month', 'Volume 2025']
monthly_last = df_last.groupby('Month').agg({'Patient Procedure Accession Number': 'count'}).reset_index()
monthly_last.columns = ['Month', 'Volume 2024']

monthly_trends = pd.merge(monthly_last, monthly_current, on='Month', how='outer').fillna(0)
monthly_trends['% of Total (2025)'] = (monthly_trends['Volume 2025'] / total_referrals) * 100
monthly_trends['% of Total (2025)'] = monthly_trends['% of Total (2025)'].round(1)

top_category_per_month = df_current.groupby('Month')['Procedure Category Description'].agg(lambda x: x.value_counts().idxmax())
monthly_trends = monthly_trends.merge(top_category_per_month, on='Month')
monthly_trends.columns = ['Month', 'Volume 2024', 'Volume 2025', '% of Total (2025)', 'Top Category (2025)']
monthly_trends.to_csv('monthly_trends.csv', index=False)
print("Monthly Trends saved to 'monthly_trends.csv'")
print(monthly_trends)

# Chart: YTD Monthly Referral Volume Trend Line Chart (Compared to Last Year)
plt.figure(figsize=(10, 6))
plt.plot(monthly_trends['Month'], monthly_trends['Volume 2025'], label='2025', marker='o')
plt.plot(monthly_trends['Month'], monthly_trends['Volume 2024'], label='2024', marker='o')
plt.title('YTD Monthly Referral Volume Trend (2025 vs 2024)')
plt.xlabel('Month')
plt.ylabel('Volume')
plt.xticks(range(1, 13))
plt.legend()
plt.grid(True)
plt.savefig('monthly_trend_chart.png')
plt.close()
print("Monthly trend chart saved to 'monthly_trend_chart.png'")

# ------------------- By Procedure Category (Modality) -------------------
category_breakdown = df_current['Procedure Category Description'].value_counts().reset_index()
category_breakdown.columns = ['Procedure Category', 'Volume']
category_breakdown['% of Total'] = (category_breakdown['Volume'] / total_referrals) * 100
category_breakdown['% of Total'] = category_breakdown['% of Total'].round(1)

# Add top example procedure per category (fixed merge logic)
top_proc_per_cat = df_current.groupby('Procedure Category Description')['Procedure Code Description'].agg(lambda x: x.value_counts().idxmax()).reset_index()
top_proc_per_cat.columns = ['Procedure Category', 'Top Procedure Code Description']
top_count_per_cat = df_current.groupby('Procedure Category Description')['Procedure Code Description'].agg(lambda x: x.value_counts().max()).reset_index()
top_count_per_cat.columns = ['Procedure Category', 'Top Procedure Count']

category_breakdown = category_breakdown.merge(top_proc_per_cat, left_on='Procedure Category', right_on='Procedure Category')
category_breakdown = category_breakdown.merge(top_count_per_cat, left_on='Procedure Category', right_on='Procedure Category')
category_breakdown['Top Procedure Example'] = category_breakdown['Top Procedure Code Description'] + ' (' + category_breakdown['Top Procedure Count'].astype(str) + ')'
category_breakdown = category_breakdown[['Procedure Category', 'Volume', '% of Total', 'Top Procedure Example']]
category_breakdown.to_csv('category_breakdown_2025.csv', index=False)
print("Category Breakdown saved to 'category_breakdown_2025.csv'")
print(category_breakdown)

# Chart: YTD Volume by Procedure Category Pie Chart
plt.figure(figsize=(8, 8))
plt.pie(category_breakdown['Volume'], labels=category_breakdown['Procedure Category'], autopct='%1.1f%%', startangle=140)
plt.title('YTD Volume by Procedure Category (2025)')
plt.axis('equal')
plt.savefig('category_pie_chart.png')
plt.close()
print("Category pie chart saved to 'category_pie_chart.png'")

# ------------------- Top Referrers (Practices and RPs) -------------------
top_practices = df_current['Visit Referring Practice'].value_counts().head(10).reset_index()
top_practices.columns = ['Practice', 'Volume']
top_practices['% of Total'] = (top_practices['Volume'] / total_referrals) * 100
top_practices['% of Total'] = top_practices['% of Total'].round(1)
# Add top RP per practice (fixed merge logic)
top_rp_per_prac = df_current.groupby('Visit Referring Practice')['Visit Referring Full Name'].agg(lambda x: x.value_counts().idxmax()).reset_index()
top_rp_per_prac.columns = ['Practice', 'Top RP Full Name']
top_rp_count = df_current.groupby('Visit Referring Practice')['Visit Referring Full Name'].agg(lambda x: x.value_counts().max()).reset_index()
top_rp_count.columns = ['Practice', 'Top RP Count']

top_practices = top_practices.merge(top_rp_per_prac, left_on='Practice', right_on='Practice')
top_practices = top_practices.merge(top_rp_count, left_on='Practice', right_on='Practice')
top_practices['Top RP Example'] = top_practices['Top RP Full Name'] + ' (' + top_practices['Top RP Count'].astype(str) + ')'
top_practices = top_practices[['Practice', 'Volume', '% of Total', 'Top RP Example']]

top_rps = df_current['Visit Referring Full Name'].value_counts().head(10).reset_index()
top_rps.columns = ['RP Name', 'Volume']

top_referrers = pd.merge(top_practices, top_rps, how='outer')  # Combined sheet
top_referrers.to_csv('top_referrers_2025.csv', index=False)
print("Top Referrers saved to 'top_referrers_2025.csv'")
print(top_practices)  # Practices
print(top_rps)  # RPs

# Chart: Top Practices by YTD Volume Bar Chart (Adjusted for long names and labels)
plt.figure(figsize=(12, 10))  # Increased height for better spacing
bars = plt.barh(top_practices['Practice'], top_practices['Volume'], color='skyblue')
plt.title('Top Practices by YTD Volume (2025)')
plt.xlabel('Volume')
plt.ylabel('Practice')
plt.gca().invert_yaxis()

# Add volume labels to the right of bars
for i, bar in enumerate(bars):
    width = bar.get_width()
    plt.text(width + max(top_practices['Volume']) * 0.01, bar.get_y() + bar.get_height()/2, 
             f'{int(width)}', va='center', ha='left', fontsize=10)

# Adjust layout to prevent cutoff
plt.subplots_adjust(left=0.4, right=0.95, top=0.95, bottom=0.1)  # More left margin for long names
plt.tick_params(axis='y', labelsize=10)  # Smaller font if needed
plt.savefig('top_practices_bar_chart.png', dpi=300, bbox_inches='tight')  # High DPI and tight bbox
plt.close()
print("Top practices bar chart saved to 'top_practices_bar_chart.png'")

# Cross-slice example: % mammography from top practice (e.g., Millennium)
if 'MILLENNIUM PHYSICIANS GROUP' in df_current['Visit Referring Practice'].values:
    mill_df = df_current[df_current['Visit Referring Practice'] == 'MILLENNIUM PHYSICIANS GROUP']
    mill_mammo_pct = (mill_df[mill_df['Procedure Category Description'] == 'MAMMOGRAPHY'].shape[0] / mill_df.shape[0]) * 100 if len(mill_df) > 0 else 0
    print(f"Millennium drives {round(mill_mammo_pct, 1)}% of its referrals in mammography.")

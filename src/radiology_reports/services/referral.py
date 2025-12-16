import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('YTD2025Referrals.csv')  # Replace with path
df['Patient Procedure Schedule Start Date'] = pd.to_datetime(df['Patient Procedure Schedule Start Date'])
df['Month'] = df['Patient Procedure Schedule Start Date'].dt.month

# Monthly Volume
monthly = df.groupby('Month').size()
monthly.plot(kind='line', title='Monthly Trend')
plt.savefig('monthly_trend.png')

# Top Practices
top_prac = df['Visit Referring Practice'].value_counts().head(10)
top_prac.plot(kind='bar', title='Top Practices')
plt.savefig('top_practices.png')

# Export sliced CSV
top_prac_df = df['Visit Referring Practice'].value_counts().reset_index()
top_prac_df.to_csv('top_practices.csv')
print(df.describe())
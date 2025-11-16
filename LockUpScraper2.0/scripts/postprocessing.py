import pandas as pd
import re
from datetime import datetime

def clean_lu_df(df: pd.DataFrame):
    '''
    Prints summary statistics. 

    Applies standard cleaning steps to data.
    '''
    def clean_str(x):
        if isinstance(x, float):
            return x
        elif isinstance(x, str): 
            x = re.sub(r'\s+', ' ', x) #Trim spaces between text items. 
            x = re.sub(r'US\s+AO', 'USAO', x) #Remove spaces between USAO which sometimes occur. 
            return x.strip()
        else:
            return x.strip()
    
    df['court_date'] = pd.to_datetime(df['court_date'])
    df['court_date'] = df.groupby('file_name')['court_date'].ffill()
    df['arresting_officer_badge'] = df['arresting_officer_badge'].apply(lambda x: re.sub(r'\s+', '', x) if isinstance(x, str) else x)
    df['prosecutor'] = df['prosecutor'].apply(clean_str)
    for col in ['true_name', 'name', 'defense_name', 'arresting_officer_name']:
        df[col] = df[col].apply(lambda x: clean_str(x).upper() if isinstance(x, str) else x)
    
    #Print Summary Statistics
    print("\n" + "="*50)
    print("📊 SUMMARY STATISTICS")
    print("="*50)
    print(df.describe(include='all').round(2))
    print("Court Dates Scraped: \n")
    print("\n".join(
        f"  • {date.strftime('%A, %Y-%m-%d')}" for date in sorted(df['court_date'].dropna().unique())))

    return df
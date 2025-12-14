import pandas as pd
import numpy as np

# Read the CSV file
df = pd.read_csv('goodreads_library_20251211_083200.csv')

# Clean the data
def clean_data(df):
    # Clean date_read: convert "not set", empty string, or np.nan to NaT; otherwise, parse to datetime
    df['date_read'] = df['date_read'].replace(['not set', '', np.nan], pd.NaT)
    df['date_read'] = pd.to_datetime(df['date_read'], errors='coerce', format="%b %d, %Y")

    # Clean date_added: convert empty string or np.nan to NaT; otherwise, parse to datetime
    df['date_added'] = df['date_added'].replace(['', np.nan], pd.NaT)
    df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce', format="%b %d, %Y")

    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    # Clean isbn: convert empty strings to None
    df['isbn'] = df['isbn'].replace('', None)
    df['isbn'] = df['isbn'].astype(str).replace('nan', None)
    
    # Clean pages: convert "unknown" and empty to None, then to integer
    df['pages'] = df['pages'].replace('unknown', None)
    df['pages'] = df['pages'].replace('', None)
    df['pages'] = pd.to_numeric(df['pages'], errors='coerce').astype('Int64')
    
    # Clean format: convert empty strings to None
    df['format'] = df['format'].replace('', None)
    
    # Ensure title is not null (required field)
    df = df[df['title'].notna()]
    
    # Strip whitespace from string columns
    string_cols = ['title', 'author', 'date_read', 'date_added', 'isbn', 'format']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', None)
            df[col] = df[col].replace('None', None)
    
    return df

# Clean the dataframe
df_clean = clean_data(df)

# Save to a new CSV file (using empty string for NULL values, which Supabase will interpret as NULL)
output_file = 'goodreads_library_cleaned.csv'
df_clean.to_csv(output_file, index=False, na_rep='')

print(f"✓ Cleaned {len(df_clean)} records")
print(f"✓ Output saved to: {output_file}")
print(f"\nSample of cleaned data:")
print(df_clean.head(10).to_string())
print(f"\nNull counts per column:")
print(df_clean.isnull().sum())
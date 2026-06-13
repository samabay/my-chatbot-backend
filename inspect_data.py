import pandas as pd
import os

def inspect_xlsx(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    try:
        # Try to read the excel file with pandas
        # We'll just read the first sheet for now
        df = pd.read_excel(file_path)
        print(f"Rows: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")
        print("\nFirst 5 rows:")
        print(df.head())
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    inspect_xlsx(r'c:\Users\User\OneDrive\Desktop\project\data.xlsx')

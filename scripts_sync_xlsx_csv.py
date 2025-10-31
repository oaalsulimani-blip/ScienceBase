# put this file at scripts/sync_xlsx_csv.py in your repo
import os
import sys
import argparse
import pandas as pd

# Default filenames (matches your confirmed file)
DEFAULT_XLSX = os.getenv('ORCID_EXCEL_FILE', 'data_ORCIDs_CORRECTED.xlsx')
DEFAULT_CSV = os.path.splitext(DEFAULT_XLSX)[0] + '.csv'

def csv_to_xlsx(csv_path=DEFAULT_CSV, xlsx_path=DEFAULT_XLSX):
    if not os.path.exists(csv_path):
        print(f"No CSV found at {csv_path}; skipping CSV->XLSX conversion.")
        return False
    try:
        df = pd.read_csv(csv_path)
        df.to_excel(xlsx_path, index=False)
        print(f"Converted CSV -> XLSX: {csv_path} -> {xlsx_path}")
        return True
    except Exception as e:
        print(f"Error converting CSV -> XLSX: {e}")
        return False

def xlsx_to_csv(xlsx_path=DEFAULT_XLSX, csv_path=DEFAULT_CSV):
    if not os.path.exists(xlsx_path):
        print(f"No XLSX found at {xlsx_path}; skipping XLSX->CSV conversion.")
        return False
    try:
        df = pd.read_excel(xlsx_path)
        df.to_csv(csv_path, index=False)
        print(f"Converted XLSX -> CSV: {xlsx_path} -> {csv_path}")
        return True
    except Exception as e:
        print(f"Error converting XLSX -> CSV: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Sync CSV and XLSX for data_ORCIDs_CORRECTED")
    parser.add_argument('--from-csv', action='store_true', help='Convert CSV -> XLSX (apply in-repo edits before running updater)')
    parser.add_argument('--to-csv', action='store_true', help='Convert XLSX -> CSV (persist updates to CSV for web editing)')
    args = parser.parse_args()

    success = True
    if args.from_csv:
        success = csv_to_xlsx() and success
    if args.to_csv:
        success = xlsx_to_csv() and success

    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
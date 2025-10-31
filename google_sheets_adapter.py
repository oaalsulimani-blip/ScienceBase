import os
import json
import tempfile
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from google.oauth2.service_account import Credentials

def _load_service_account_creds():
    """Load service account JSON from env var and return Credentials."""
    sa_json = os.getenv('GSPREAD_SERVICE_ACCOUNT_JSON')
    if not sa_json:
        raise RuntimeError("GSPREAD_SERVICE_ACCOUNT_JSON environment variable not set")
    # Save to a temp file because gspread can accept credentials from dict/credentials object
    info = json.loads(sa_json)
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return creds

def read_sheet_to_df(spreadsheet_id_or_url, worksheet_name=None):
    """Return a pandas DataFrame of the sheet contents."""
    creds = _load_service_account_creds()
    client = gspread.authorize(creds)
    if '/' in spreadsheet_id_or_url and 'spreadsheets' in spreadsheet_id_or_url:
        ss = client.open_by_url(spreadsheet_id_or_url)
    else:
        ss = client.open_by_key(spreadsheet_id_or_url)
    if worksheet_name:
        sheet = ss.worksheet(worksheet_name)
    else:
        sheet = ss.get_worksheet(0)
    df = get_as_dataframe(sheet, evaluate_formulas=True, header=0)
    # Drop fully empty rows commonly returned by get_as_dataframe
    return df.dropna(how='all')

def write_df_to_sheet(df, spreadsheet_id_or_url, worksheet_name='Sheet1', clear_first=True):
    """Write a pandas DataFrame back to the worksheet (creates if missing)."""
    creds = _load_service_account_creds()
    client = gspread.authorize(creds)
    if '/' in spreadsheet_id_or_url and 'spreadsheets' in spreadsheet_id_or_url:
        ss = client.open_by_url(spreadsheet_id_or_url)
    else:
        ss = client.open_by_key(spreadsheet_id_or_url)

    try:
        worksheet = ss.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = ss.add_worksheet(title=worksheet_name, rows="100", cols="20")

    if clear_first:
        worksheet.clear()

    set_with_dataframe(worksheet, df, include_index=False, include_column_header=True)

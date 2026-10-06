from dotenv import load_dotenv
from os import environ
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pathlib import Path

load_dotenv()

creds = Credentials.from_service_account_file(
    f"{Path(__file__).parent}/service_account_credentials.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
service = build("sheets", "v4", credentials=creds)
google_sheet_id = environ["GOOGLE_SHEET_ID"]

headers = service.spreadsheets().values().get(
                spreadsheetId=google_sheet_id,
                range="Gastos!1:1"
            ).execute()["values"][0]

table_rows_as_list = service.spreadsheets().values().get(
        spreadsheetId=google_sheet_id,
        range="Gastos!A:I"
    ).execute()["values"]

table_rows_as_list.pop(0)

table_rows_as_dict = [
    dict(zip(headers,row)) for row in table_rows_as_list
]

print("headers", headers)
print("rows", table_rows_as_dict)
#!/usr/bin/python3

import requests
import json
from googleapiclient import discovery
from google.oauth2 import service_account
import os
import logging
import sys

logging.basicConfig(filename="autoUpdate.log", format='%(asctime)s - %(levelname)s: %(message)s', level=logging.INFO)


def get_results(cred_path: str):
    logging.info("Getting latest results from football-data.org")

    uri = "https://api.football-data.org/v4/competitions/PL/matches?season=2022&status=FINISHED"
    api_key = generate_football_data_credentials(cred_path)
    headers = {"X-Auth-Token": api_key}

    res_raw = requests.get(uri, headers=headers)
    res_extract = res_raw.json()["matches"]

    return res_extract


def generate_football_data_credentials(cred_path: str):
    file = open(cred_path + "football-data-credentials.json")
    data = json.load(file)["api_key"]
    file.close()

    return data


def generate_google_credentials(cred_path: str):
    scopes = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file",
              "https://www.googleapis.com/auth/spreadsheets"]
    secret_file = os.path.join(os.getcwd(), cred_path + "google-credentials.json")
    credentials = service_account.Credentials.from_service_account_file(secret_file, scopes=scopes)

    return credentials


def get_sheets_results(sheet_range: str, cred_path: str):
    logging.info("Getting latest scores from Google Sheets")

    spreadsheet_id = "11EmqTM3AMsaeZ3h9tYVb0MNfUCVPNe-y9SlRolCHp2E"
    credentials = generate_google_credentials(cred_path)
    service = discovery.build('sheets', 'v4', credentials=credentials)

    auth_res_raw = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_range).execute()
    auth_res_filtered = auth_res_raw["values"]

    return auth_res_filtered


def post_updated_results(sheet_range: str, updated_results: list):
    logging.info("Posting updated scores to Google Sheets")

    spreadsheet_id = "11EmqTM3AMsaeZ3h9tYVb0MNfUCVPNe-y9SlRolCHp2E"
    data = {"values": updated_results}
    credentials = generate_google_credentials()

    service = discovery.build('sheets', 'v4', credentials=credentials)

    res = service.spreadsheets().values()\
        .update(spreadsheetId=spreadsheet_id, body=data, range=sheet_range, valueInputOption="USER_ENTERED").execute()

    logging.info(res)


# For testing against a json file
def get_results_file(filename: str):
    file = open(filename)
    data = json.load(file)
    file.close()

    return data


# To reconcile team name difference between the two data sources, allowing them to be searched against each other
def format_team_names(orig_name: str):
    if orig_name == "Brighton Hove":
        return "Brighton"
    elif orig_name == "Leeds United":
        return "Leeds"
    elif orig_name == "Leicester City":
        return "Leicester"
    elif orig_name == "Man United":
        return "Man Utd"
    elif orig_name == "Nottingham":
        return "Nottingham Forest"
    elif orig_name == "Tottenham":
        return "Spurs"
    elif orig_name == "Wolverhampton":
        return "Wolves"
    else:
        return orig_name


def update_scores(results, matches):
    updated_matches = matches
    for match in updated_matches:
        if len(match) == 2:
            for result in results:
                if match[0] == format_team_names(result["homeTeam"]["shortName"]) \
                        and match[1] == format_team_names(result["awayTeam"]["shortName"]):
                    res = str(result["score"]["fullTime"]["home"]) + "-" + str(result["score"]["fullTime"]["away"])
                    match.append(res)
    return updated_matches


if __name__ == "__main__":
    range_name_test: str = "AutoUpdateTest!D3:F382"
    range_name: str = "EngineRoom!F4:H383"
    cred_path = sys.argv[1]

    # Get results and matches to be updated
    fd_res_live_test = get_results(cred_path)
    gs_res_live_test = get_sheets_results(range_name_test, cred_path)

    # Update Google Sheets object with the latest scores
    updated = update_scores(fd_res_live_test, gs_res_live_test)

    # Post updated object to Google Sheets.
    #   This will appear to update the entire 380 game list, but if there are no scores available it will only 'update'
    #   the team names
    post_updated_results(range_name_test, updated)

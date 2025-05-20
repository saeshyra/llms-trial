import os
import subprocess
import mysql.connector
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import user_profiling_layer as upl
from dotenv import load_dotenv
import json
import requests
from time import sleep

load_dotenv("./credentials.env")
# Retrieve credentials from environment variables
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

mydb = mysql.connector.connect(
    host="localhost",
    user=DB_USERNAME,
    password=DB_PASSWORD
)

# define the scope
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name('chatbot_trial_creds.json', scope)

# authorize the clientsheet
client = gspread.authorize(creds)

# get the instance of the Spreadsheet
sheet = client.open('Diet Coaching Chatbot Trial Form Responses')

# get the first sheet of the Spreadsheet
sheet_instance = sheet.worksheet('Trial Information')
records = sheet_instance.get_all_records()
for record in records:
    if record['Telegram'] and record['MFP']:# and record['Group']:
        timezones = {
            'Americas (Eastern Daylight Time - EDT, GMT-4)': 'EDT',
            'Europe / North Africa (Central European Summer Time - CEST, GMT+2)': 'CEST',
            'South Asia (India Standard Time - IST, GMT+5:30)': 'IST',
            'Australia / East Asia\xa0(Australian Eastern Standard Time - AEST, GMT+10)': 'AEST'
        }
        _, _, _, sender_id, group_num, _ = upl.preferences_management_module.get_user_from_db(telegram_user=record['Telegram'].strip()) # if they already have one
        upl.preferences_management_module.add_user_to_db(record['Telegram'].strip(),
                                                         record['MFP'].strip(),
                                                         record['First name'].strip(),
                                                         sender_id,
                                                         record['Group'] if record['Group'] else None,
                                                         timezones[record['Time zone']] if record['Time zone'] else 'CEST')
    
        # resume conversations
        if record['Group'] and not group_num and sender_id:
            print(f"Resume conversation for {record['Telegram'].strip()} in group {record['Group']} after in database as group {group_num}")
            url = f'http://localhost:5005/conversations/{sender_id}/tracker/events'
            headers = {"Content-Type": "application/json"}

            # response = requests.post(url, headers=headers, data=json.dumps({"event": "resume"}))
            # if response.status_code != 200:
            #     print('\n**************************************************')
            #     print(f"Failed to resume conversation for {record['Telegram']}. Status code:", response.status_code)
            #     print('Response:', response.text)
            #     print('**************************************************\n')

            response = requests.post(url, headers=headers, data=json.dumps({"event": "restart"}))
            if response.status_code != 200:
                print('\n**************************************************')
                print(f"Failed to restart conversation for {record['Telegram'].strip()}. Status code:", response.status_code)
                print('Response:', response.text)
                print('**************************************************\n')
                
            sleep(3)

            url = f'http://localhost:5005/conversations/{sender_id}/trigger_intent?output_channel=telegram'
            response = requests.post(url, headers=headers, data=json.dumps({"name": "trial_start"}))
            if response.status_code != 200:
                print('\n**************************************************')
                print(f"Failed to send followup messages to {record['Telegram'].strip()}. Status code:", response.status_code)
                print('Response:', response.text)
                print('**************************************************\n')
            
            sleep(3)


# browser = subprocess.run(['google-chrome-stable','https://www.myfitnesspal.com/'])
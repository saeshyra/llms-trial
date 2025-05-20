import argparse
import requests
import signal
import subprocess
import time
import yaml
import mysql.connector
from datetime import datetime, timedelta
from time import sleep
from pyngrok import ngrok
from multiprocessing import set_start_method
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import user_profiling_layer as upl

ap = argparse.ArgumentParser(description='Run diet coaching chatbot')
ap.add_argument('--db-setup', default=False, action='store_true', help='SQL database setup')
ap.add_argument('--mfp-setup', default=False, action='store_true', help='MFP master account setup')
ap.add_argument('--rasa-train', default=False, action='store_true', help='Rasa model training')

class Service(object):

    def __init__(self):
        self.session = requests.Session()

    def get_info(self):
        uri = "http://localhost:4040/api/tunnels"
        response = self.session.get(uri)
        if response.status_code == 200:
            return response
        else:
            response.raise_for_status()

    def close(self):
        self.session.close()

def inject_credentials(service):
    r = service.get_info()

    #injecting credentials with ngrok dynamic URL
    with open('credentials.yml', 'r') as stream:
        credentials = yaml.load(stream, Loader=yaml.BaseLoader)
    for t in r.json()['tunnels']:
        if 'ngrok' in t['public_url']:
            credentials['telegram']['webhook_url'] = f'''{t['public_url']}/webhooks/telegram/webhook/'''
            break
        elif 'public url' in t:
            credentials['telegram']['webhook_url'] = f'''{t['public_url']}/webhooks/telegram/webhook/'''
    with open('credentials.yml', 'w') as stream:
        yaml.dump(credentials, stream)


def main(args: argparse.Namespace):
    service = Service()
    
    # Load environment variables from a .env file
    load_dotenv("./credentials.env")

    # Retrieve credentials from environment variables
    DB_USERNAME = os.getenv("DB_USERNAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    set_start_method("spawn")
    start_session = datetime.now()
    ngrok_expiration = start_session + timedelta(minutes=20)

    while True:
        try:
            # sudo requires the flag '-S' in order to take input from stdin
            proc = subprocess.run("killall docker".split())
            proc = subprocess.run("fuser -k 8000/tcp".split())
            proc = subprocess.run("killall ngrok".split())
            proc = subprocess.run("fuser -k 5055/tcp".split())
            # Popen only accepts byte-arrays so you must encode the string
            
            mydb = mysql.connector.connect(
                host="localhost",
                user=DB_USERNAME,
                password=DB_PASSWORD
            )
            if args.db_setup:
                with open('create.sql', 'r') as f:
                    with mydb.cursor() as cursor:
                        cursor.execute(f.read(), multi=True)
                cursor.close()

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
                    # extract sender_id if they already have one
                    _, _, _, sender_id, _, _ = upl.preferences_management_module.get_user_from_db(telegram_user=record['Telegram'].strip())
                    
                    upl.preferences_management_module.add_user_to_db(record['Telegram'].strip(),
                                                                     record['MFP'].strip(), 
                                                                     record['First name'].strip(),
                                                                     sender_id,
                                                                     record['Group'] if record['Group'] else None,
                                                                     timezones[record['Time zone']] if record['Time zone'] else 'CEST')

            from pyngrok import conf
            config = conf.PyngrokConfig()
            print(config.ngrok_path)

            http_tunnel = ngrok.connect(bind_tls=True, addr=5005)
            docker = subprocess.Popen(['docker', 'run', '-p', '8000:8000', 'rasa/duckling'])
            actions = subprocess.Popen(['rasa', 'run', 'actions'])
            sleep(3)

            print('Connection timer is low, if something doesn\'t work try increasing it from main')

            if args.mfp_setup:
                print('Opening browser')
                browser = subprocess.run(['google-chrome-stable','https://www.myfitnesspal.com/'])

            if args.rasa_train:
                train = subprocess.Popen(['rasa', 'train'])
                train.wait()

            print('injecting')
            inject_credentials(service)
            print('running RASA')
            rasa = subprocess.Popen(['rasa', 'run', '--enable-api'])#, '--debug'])

            while True:

                # if datetime.now() >= ngrok_expiration:
                #     print('killing RASA')
                #     proc = subprocess.run("killall rasa".split())
                #     print('killing NGROK')
                #     ngrok.kill()
                #     # sleep(2)
                #     print('re-running NGROK')
                #     http_tunnel = ngrok.connect(5005)
                #     # sleep(3)
                #     print('injecting')
                #     inject_credentials()
                #     rasa = subprocess.Popen(['rasa', 'run', '--enable-api'])#, '--debug'])
                #     # sleep(3)
                #     actions = subprocess.Popen(['rasa', 'run', 'actions'])
                #     start_session = datetime.now()
                #     ngrok_expiration = start_session + timedelta(minutes=20)
                #     print(f'done, new expiration: {ngrok_expiration}')

                continue
        
        except Exception as e:
            print(f'\n******************************\nPROGRAM CRASHED, RESTARTING...\n{e}\n******************************\n')
            service.close()
            sleep(10)
            continue


    rasa.send_signal(signal.SIGINT)
    actions.send_signal(signal.SIGINT)
    docker.send_signal(signal.SIGINT)
    ngrok.send_signal(signal.SIGINT)

    rasa.wait()
    actions.wait()
    docker.wait()
    ngrok.wait()

if __name__ == '__main__':
    args = ap.parse_args([] if "__file__" not in globals() else None)
    main(args)

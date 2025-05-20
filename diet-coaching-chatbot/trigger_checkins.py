import json
import requests
import pandas as pd
from time import sleep
from datetime import datetime, timedelta
from pytz import timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from functools import partial
from user_profiling_layer.preferences_management_module import get_all_users_from_db

CHECKIN_HOUR = 9
CHECKIN_NUMBER = 7

timezones = {
    'EDT': timezone('America/New_York'),
    'CEST': timezone('Europe/Berlin'),
    'IST': timezone('Asia/Kolkata'),
    'AEST': timezone('Australia/Sydney')
}

def trigger_intent(intent, sender_id):
    url = f'http://localhost:5005/conversations/{sender_id}/trigger_intent?output_channel=telegram'
    headers = {"Content-Type": "application/json"}
    
    attempts = 5
    for attempt in range(attempts):
        response = requests.post(url, headers=headers, data=json.dumps({"name": intent}))
        if response.status_code == 200:
            sleep(2)
            break
        
        # skip error sleep on last try
        if attempt == attempts - 1:
            continue

        # there is some error, wait 3 seconds
        sleepTime = 3
        if response.status_code == 429:
            sleepTime += response.json()['parameters']['retry_after']
        sleep(sleepTime)
        
    else: # if all attempts failed
        print('\n**************************************************')
        print(f'Failed to trigger {intent} intent for {sender_id}. Status code:', response.status_code)
        print('Response:', response.text)
        print('**************************************************\n')
        
    return

users = get_all_users_from_db()
start_dates = {}
for i in range(15, 23):
    start_dates.update({row['telegram_user']: i for _, row in pd.read_csv(f'start_dates/usernames_{i}.csv').iterrows()})

scheduler = BlockingScheduler()

min_offset = 0
for telegram_user, mfp_user, _, sender_id, user_group, user_timezone in users:
    if sender_id and telegram_user in start_dates:

        # 7 weekly check-ins
        run_date = datetime(year=2024, month=5, day=start_dates[telegram_user], hour=CHECKIN_HOUR, minute=min_offset)
        run_date += timedelta(days=7*CHECKIN_NUMBER)
        # for week in range(7):
        trigger_checkin = partial(trigger_intent, f'prompt_week{CHECKIN_NUMBER}_checkin', sender_id)
        scheduler.add_job(trigger_checkin, 'date', run_date=run_date, timezone=timezones[user_timezone], name=f'{telegram_user}_week{CHECKIN_NUMBER}_checkin')
        
    min_offset += 2
    min_offset %= 60
    
scheduler.print_jobs()
scheduler.start()

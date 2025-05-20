import json
import requests
import pandas as pd
from time import sleep
from pytz import timezone
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from functools import partial
import myfitnesspal as mfp
from user_profiling_layer.preferences_management_module import *

TRIAL_FIRST_DAY = datetime(2024, 5, 15)
MAX_TIME_BETWEEN_INTERACT = timedelta(hours=36)
CHECK_LAST_INTERACT_HOUR = 18

ADMIN_USER = 'saeshyra'

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

def check_empty_diary(mfp_user, telegram_user, sender_id):
    day = datetime.today()

    for i in range(10):  # try up to 10 times in case the client does not connect
        # print(f'{i+1} attempts to connect to mfp')
        client = mfp.Client()
        data = client.get_date(day.year, day.month, day.day, username=mfp_user)
        if data.keys(): # meal names
            print(f'{telegram_user}: {i+1} attempts to connect to mfp')
            break
    
    if not data.keys():
        print(f"NO ACCESS to {telegram_user}'s mfp diary")
        return

    # check if diary is empty
    if (data.totals == {}):
        trigger_intent('prompt_fill_diary', sender_id)
        # sleep(10)
        # notify_prompt_fill_diary(telegram_user)

    return

def notify_prompt_interact(telegram_user):
    admin_sender_id = get_user_from_db(telegram_user=ADMIN_USER)[3]

    url = f'http://localhost:5005/conversations/{admin_sender_id}/trigger_intent?output_channel=telegram'
    headers = {"Content-Type": "application/json"}
    intent = {
        "name": "notify_prompt_interact",
        "entities": {
            "telegram_user": telegram_user.replace("_", "\\_")
        }
    }
    attempts = 5
    for attempt in range(attempts):
        response = requests.post(url, headers=headers, data=json.dumps(intent))
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
        print(f'Failed to trigger notify_prompt_interact intent for {telegram_user}. Status code:', response.status_code)
        print('Response:', response.text)
        print('**************************************************\n')
        
    return

def check_last_interact(telegram_user, sender_id):
    last_interaction = None
    
    user_query = f'''
        SELECT JSON_UNQUOTE(JSON_EXTRACT(data, '$.timestamp')) AS timestamp
        FROM events
        WHERE JSON_EXTRACT(data, '$.sender_id') = '{sender_id}'
        AND JSON_EXTRACT(data, '$.event') = 'user'
        AND JSON_EXTRACT(data, '$.metadata.message.text') NOT LIKE '/%';
    '''

    with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
        with connection.cursor() as cursor:
            cursor.execute(user_query)
            rows = cursor.fetchall()

    timestamps = [datetime.fromtimestamp(float(row[0])) for row in rows if row]
    timestamps.sort(reverse=True)
    if timestamps:
        last_interaction = timestamps[0]
    else:
        last_interaction = TRIAL_FIRST_DAY
    print(f"{telegram_user}'s last interaction:", last_interaction)

    if datetime.now() - last_interaction > MAX_TIME_BETWEEN_INTERACT:
        trigger_intent('prompt_interact', sender_id)
        sleep(10)
        notify_prompt_interact(telegram_user)

    return


users = get_all_users_from_db()
start_dates = {}
for i in range(15, 22):
    start_dates.update({row['telegram_user']: i for _, row in pd.read_csv(f'start_dates/usernames_{i}.csv').iterrows()})

scheduler = BlockingScheduler()

run_date = datetime.now()
run_date += timedelta(seconds=10)
for telegram_user, mfp_user, _, sender_id, user_group, user_timezone in users:
    if sender_id and telegram_user in ['katharinatrinley', 'SV36p']:
        
        # check for empty food diary
        # perform_check_empty_diary = partial(check_empty_diary, mfp_user, telegram_user, sender_id)
        # scheduler.add_job(perform_check_empty_diary, 'date', run_date=run_date, name=f'{telegram_user}_empty_diary')
        
        # check for abnormal food diary
        perform_check_abnormal_diary = partial(trigger_intent, 'prompt_check_diary', sender_id)
        scheduler.add_job(perform_check_abnormal_diary, 'date', run_date=run_date, name=f'{telegram_user}_abnormal_diary')
        
        # check whether user has recently interacted with the chatbot
        # perform_check_last_interact = partial(check_last_interact, telegram_user, sender_id)
        # scheduler.add_job(perform_check_last_interact, 'date', run_date=run_date, name=f'{telegram_user}_last_interact')

        
        run_date += timedelta(minutes=2)
    
scheduler.print_jobs()
scheduler.start()

import json
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from functools import partial
from user_profiling_layer.preferences_management_module import get_user_from_db

ADMIN_USER = 'saeshyra'
INTERVAL = 10

def trigger_intent(intent, sender_id):
    url = f'http://localhost:5005/conversations/{sender_id}/trigger_intent?output_channel=telegram'
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps({"name": intent}))
    
    if response.status_code == 200:
        print(f'Intent {intent} triggered for {sender_id}.')
    else:
        print(f'Failed to trigger {intent} intent for {sender_id}. Status code:', response.status_code)
        print('Response:', response.text)
    return

scheduler = BlockingScheduler()

user = get_user_from_db(telegram_user=ADMIN_USER)
min_offset = 0
telegram_user, mfp_user, _, sender_id, user_group, user_timezone = user

for minute in range(0, 60, INTERVAL):
    send_message = partial(trigger_intent, 'greet', user[3])
    scheduler.add_job(send_message, 'cron', minute=minute)

scheduler.start()

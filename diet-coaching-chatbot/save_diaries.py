import json
import requests
from time import sleep
from pytz import timezone
from datetime import datetime, timedelta
from functools import partial
import myfitnesspal as mfp
from user_profiling_layer.preferences_management_module import *


ADMIN_USER = 'saeshyra'

timezones = {
    'EDT': timezone('America/New_York'),
    'CEST': timezone('Europe/Berlin'),
    'IST': timezone('Asia/Kolkata'),
    'AEST': timezone('Australia/Sydney')
}

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

    return

users = get_all_users_from_db()
        
min_offset = 0
for telegram_user, mfp_user, _, sender_id, user_group, user_timezone in users:
    if sender_id:

        # prompt nutritional counselling weekly
        if user_group==3:
            trigger_counselling = partial(trigger_intent, 'prompt_counselling', sender_id)
            scheduler.add_job(trigger_counselling, 'cron', name=f'{telegram_user}_counselling',
                              day_of_week=COUNSELLING_DAY, hour=COUNSELLING_HOUR, minute=min_offset, timezone=timezones[user_timezone])

        # check for empty food diary
        perform_check_empty_diary = partial(check_empty_diary, mfp_user, telegram_user, sender_id)
        scheduler.add_job(perform_check_empty_diary, 'cron', name=f'{telegram_user}_empty_diary',
                          hour=CHECK_EMPTY_DIARY_HOUR, minute=min_offset, timezone=timezones[user_timezone])

        # check for abnormal food diary
        perform_check_abnormal_diary = partial(trigger_intent, 'prompt_check_diary', sender_id)
        scheduler.add_job(perform_check_abnormal_diary, 'cron', name=f'{telegram_user}_abnormal_diary',
                          hour=CHECK_ABNORMAL_DIARY_HOUR, minute=min_offset, timezone=timezones[user_timezone])

        # check whether user has recently interacted with the chatbot
        perform_check_last_interact = partial(check_last_interact, telegram_user, sender_id)
        scheduler.add_job(perform_check_last_interact, 'cron', name=f'{telegram_user}_last_interact',
                          hour=CHECK_LAST_INTERACT_HOUR, minute=min_offset, timezone=timezones[user_timezone])
        
    min_offset += 2
    min_offset %= 60

scheduler.print_jobs()
scheduler.start()

import datetime
import multiprocessing
import numpy as np
import math
from joblib import Parallel, delayed
from itertools import chain


empty_day_struct = {

}

def parse_totals(meal):
    if meal.totals != {}:
        return meal.totals
    else:
        return {'calories': 0,
                'carbohydrates': 0,
                'fat': 0,
                'protein': 0,
                'sodium': 0,
                'sugar': 0,
                'foods': []
                }

def scrap_day_data(args):
    client = args[0]
    dates = args[1]
    username = args[2]

    scraped_data = []

    for date in dates:
        if type(date) != datetime.date:
            date = datetime.date(date)
        day = client.get_date(date, username=username)

        scraped_data.append({
            'day_id': day.date.isoformat(),
            'goals': day.goals,
            'totals': day.totals,
            'meals': [{
                **parse_totals(meal),
                #some foods does not have a short name so full name must be used (maybe cut the string). If serving is not available nothing can be done.
                'foods': [
                    {'name': (food.short_name) if food.short_name else food.name, 'unit': (food.unit) if food.unit else 'Serving N/A', 'quantity': (food.quantity) if food.quantity else 0, **food.totals}
                    for food in meal.entries
                ]
            } for meal in day.meals]
        })
    return scraped_data


def scrap(client, username, dates):
    if type(dates[0]) == list:
        dates = list(chain.from_iterable(dates))

    data = []
    if dates:
        dates_number = len(dates)
        if dates_number == 1:
            #args  = [client,dates[0],username]
            args  = [client,[dates[0]],username]
            data = scrap_day_data(args)
        else:
            # print('need to scrap multiple days')
            for i in range(5):  # retry in case of failed MFP API call (sometimes connection gets rejected/reset)
                try:
                    dates_number = len(dates)
                    cpu_cores = int(multiprocessing.cpu_count())
                    if cpu_cores > 10:
                        cpu_cores = 10
                    # print(f'{cpu_cores} cores available')
                    individual_workload = math.ceil(dates_number / cpu_cores)
                    # print(f'{individual_workload} jobs per core')
                    workload = np.array_split(dates, cpu_cores)
                    jobs = [[client, job, username] for job in workload]
                    res = Parallel(n_jobs=cpu_cores, backend="threading", timeout=10)(delayed(scrap_day_data)(x) for x in jobs)

                    for el in res:
                        data.extend(el)
                    left_days = list(filter(lambda el: el.isoformat() not in [day['day_id'] for day in data],
                                            dates))
                    if len(left_days) == 0:
                        break
                    else:
                        dates = left_days
                        dates_number = len(dates)
                except Exception as e:
                    print('ERROR AT DATA-HANDLING level:')
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(e).__name__, e.args)
                    print(message)
                    continue

    return data


def scrap_user_basic_info(client, username):
    user_profile = {
        'user_name': username,
        'energy_unit': 'calories', #impossible to get this while using public diaries, TODO: find a way or just convert
        'meal_names': client.get_date(2000,1,1, username=username).keys() #dummy day access to get meal names
    }

    return user_profile

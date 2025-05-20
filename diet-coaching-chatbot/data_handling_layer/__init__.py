
import numpy as np
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from datetime import date
from data_handling_layer import data_scraping_module as scraper
from data_handling_layer import data_analysis_module as analyser
from data_handling_layer import data_aggregation_module as aggregator
from data_handling_layer import data_management_module as manager
from data_handling_layer import data_comparison_module as comparator
from data_handling_layer import data_visualization_module as visualiser
import user_profiling_layer as upl
import myfitnesspal as mfp
from datetime import datetime, timedelta

global client_session
global expiration_date
client = None
expiration_date = None
#master_account = 'philhealthybot'
#password = 't5QrU!TEq@Re'

def handle_client(username):
    global master_account, password
    day = datetime.now()
    for i in range(10): # try up to 10 times in case the client does not connect
        client = mfp.Client()
        data = client.get_date(day.year, day.month, day.day, username=username)
        if data.keys(): # meal names
            print(f'{i+1} attempts to connect to mfp')
            break
    else:
        return 'mfp_error'
    
    #now = datetime.now()
    #client, expiration_date = upl.preferences_management_module.get_user_from_db(username)

    #if client != None:
    #    client = jsonpickle.decode(client)
    #if any(i is None for i in [client, expiration_date]) or now >= expiration_date:
        #print('generating new MFP client')
        #client = mfp.Client(master_account, password)
        #Since Aug 2022, MFP puts an invisible captcha that makes classic log impossible.
        #This python API (v2.0) retrieves the login cookie from the browser. It is necessary to login at least one time (don't know if it will elapse)
        #client = mfp.Client()
        #expiration_date = now + timedelta(minutes=45)
        #json_client = jsonpickle.encode(client)
        #upl.preferences_management_module.add_user_to_db(username, json_client, expiration_date)
    #else:
    #    print('using old MFP client')
    return client


def update(username, dates, keys):
    global master_account
    client = handle_client(username)
    if client == 'mfp_error':
        return 'mfp_error'

    #data = scraper.scrap_user_basic_info(client, username)
    #manager.db_write_user(data)
    data = manager.db_read_user_prefs(username) #just a check left by the two students I guess? TODO: verify and remove

    if keys:
        data['keys'] = keys
    data['days'] = scraper.scrap(client, username, dates)
    #TODO: day structure is incomplete, non-empty days appear empty because, while re-reading from DB (btw why?) food details are lost
    manager.db_write_days(
        username,
        data['energy_unit'],
        data['days']
    )
    data['days'] = manager.db_read_days(
        username,
        data['energy_unit'],
        [day['day_id'] for day in data['days']]
    )
    # if len(data['days']) > 1:
    data = handle_missing_data(data)
    # else:
    #     data.update({'MI': False})
    #     data.update({'shrinked': False})
    if type(data) != str:
        aggregator.aggregate(data)
        analyser.analyse(data)
    return data


def compare(username, less_recent, more_recent, keys):
    global master_account, password
    client = handle_client(username)
    if client == 'mfp_error':
        return 'mfp_error'
    
    data = scraper.scrap_user_basic_info(client, username)
    manager.db_write_user(data)
    data = manager.db_read_user_prefs(username)

    if keys:
        data['keys'] = keys

    dates = {
        'less_recent': less_recent,
        'more_recent': more_recent
    }

    for period in ['less_recent', 'more_recent']:
        data['days'] = scraper.scrap(client, username, dates[period])
        manager.db_write_days(
            username,
            data['energy_unit'],
            data['days']
        )
        data[period] = {'days': manager.db_read_days(
                    username,
                    data['energy_unit'],
                    [day['day_id'] for day in data['days']]
        )}
        data[period] = handle_missing_data(data[period])
        if type(data[period]) != str:
            aggregator.aggregate(data[period])
            analyser.analyse(data[period])
        else:
            return data[period]

    comparator.compare(data)
    return data


def handle_missing_data(data):

    #TODO: move into a proper structure
    MI_thresholds = {
        (1,3) : 0,
        (3,7) : 20,
        (7,14) : 30,
        (15, 365): 40#for any higher amount of days 40 % of missing data is always acceptable
    }

    # handling missing data
    empty_days = list(filter(lambda el: el['totals']['energy']['quantity']==0, data['days']))
    #MFP changed the structure, this is now just "calories"
    #empty_days = list(filter(lambda el: el['totals'] == {} or el['totals']['calories']==0, data['days']))

    data.update({'MI': False})
    data.update({'shrinked': False})

    if len(empty_days) == len(data['days']):
        return "empty"
    else:
        holes = []
        for day in list(map(lambda el: el['day_id'], empty_days)):
            if holes:
                lst_hole = holes[-1] if len(holes) > 1 else holes[0]
                lst_day = lst_hole[-1] if len(lst_hole) > 1 else lst_hole[0]
                step = timedelta(days=1)
                if date.fromisoformat(lst_day) + step == date.fromisoformat(day):
                    lst_hole.append(day)
                else:
                    holes.append([day])
            else:
                holes.append([day])

        if holes:
            #print(f'holes: {holes}')
            #print(str(len(holes)) + ' holes before popping')
            # first and last holes are valid only if they cut the "outside" of the date range
            fst_hole = holes.pop(0) if len(holes) > 0 and holes[0][0] == data['days'][0]['day_id'] else []
            lst_hole = holes.pop() if len(holes) > 1 and holes[-1][0] == data['days'][-1]['day_id'] else []
            print(str(len(holes)) + ' holes after popping')
            data['shrinked'] = False if (not fst_hole and not lst_hole) else (fst_hole if fst_hole else [] + lst_hole  if lst_hole else [])
            data['days'] = list(filter(lambda el: el['day_id'] not in fst_hole and el['day_id'] not in lst_hole, data['days']))  # TODO: user must be warned about this!
            total_days_n = len(data['days'])
            empty_days_n = sum([len(l) for l in holes])
            if empty_days_n > 0:
                for (lower, upper), thresh in MI_thresholds.items():
                    if total_days_n in range(lower, upper + 1):
                        if empty_days_n * 100 / total_days_n <= thresh:
                            data.update({'MI': True})
                        break

                    #if not data['MI'] and total_days_n > list(MI_thresholds.keys())[-1][1]:
                    #    if empty_days_n * 100 / total_days_n <= 40:
                    #        data.update({'MI': True})
                    #    break

                if not data['MI']:
                    return "most_data_missing"


            # MI of feature to predict missing data
            if data['MI']:
                estimator = BayesianRidge()
                data_to_transform = []
                for day in data['days']:
                    el = []
                    for k, v in day['totals'].items():
                        if day in empty_days:
                            el.append((np.NAN))
                        else:
                            el.append(v['quantity'])
                            #el.append(v)
                    data_to_transform.append(el)

                imp = IterativeImputer(estimator=estimator, max_iter=10, random_state=123)
                imp.fit_transform(data_to_transform)
                np.set_printoptions(suppress=True)
                data_to_transform = (np.round(imp.transform(data_to_transform)).astype(int)).tolist()

                for day in data['days']:
                    day_from_MI = data_to_transform.pop(0)
                    for key in day['totals']:
                        day['totals'][key]['quantity'] = day_from_MI.pop(0)

    if all(day['totals'] == 0 for day in data['days']):
        return "empty"

    return data

def check_diary(username):
    day = datetime.today() - timedelta(days=1)

    client = handle_client(username)
    if client == 'mfp_error':
        return 'no mfp access'
    data = client.get_date(day.year, day.month, day.day, username=username)
    
    # check whether diary is empty
    if not data.totals:
        return 'empty'

    total_food_items = 0
    for meal in data.meals:
        for food in meal.entries:
            total_food_items += 1
            # check logged portions of every food item
            if food.unit and food.quantity:
                try:
                    quantity = float(food.quantity)
                except:
                    continue

                # more than 1kg
                if (food.unit.lower() in ['kg', 'kgs', 'kilogram', 'kilograms'] and quantity >= 1) or \
                (food.unit in ['g', 'gram', 'grams'] and quantity > 1000):
                    return 'a food item with more than 1 kilogram'
                
                # more than 2L
                if (food.unit.lower() in ['l', 'ls', 'litre', 'liter', 'litres', 'liters'] and quantity >=2) or \
                   (food.unit.lower() in ['ml', 'mls', 'millilitre', 'milliliter', 'millilitres', 'milliliters', 'mililitre', 'mililiter', 'mililitres', 'mililiters'] and quantity >=2000):
                    return 'a food item with more than 2 litres'
                
                # more than 6 cups
                if food.unit in ['cup', 'cups'] and quantity > 6:
                    return 'a food item with more than 6 cups'

            # check whether singular food item consists of more than calorie goal
            if food['calories'] > data.goals['calories']:
                return 'a food entry with more than your calorie goal'

    # check if 3 or less food items total
    if total_food_items < 4:
        return 'less than 4 food items'

    # check whether calories are under 50% of calorie goal
    if data.totals['calories'] <= 0.5*data.goals['calories']:
        return 'less than half of your calorie goal'
    
    # check whether calories are over 200% of calorie goal
    if data.totals['calories'] >= 2*data.goals['calories']:
        return 'more than twice your calorie goal'

    return None
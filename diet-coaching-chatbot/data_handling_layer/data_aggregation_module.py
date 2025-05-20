import pandas
import pathos.multiprocessing
import statistics


def _mean(data):
    try:
        return statistics.mean(data)
    except statistics.StatisticsError:
        return 0.


def _aggregate_day(day):
    #day = day[0]
    foods_aggr = []
    for meal in day['meals']:
        #meal_id = list(meal.keys())[0]
        #meal = list(meal.values())[0]
        foods = [food for food in meal['foods']]
        foods_aggr.extend(foods)
        meal['foods'][:] = pandas.DataFrame(foods).groupby(
            ['name', 'unit']
        ).sum().astype(int).reset_index().to_dict('records') if foods else []

    foods = [food for meal in day['meals'] for food in meal['foods']]
    #foods = [food for food in foods_aggr if food !=[]]

    day['foods'] = pandas.DataFrame(foods).groupby(
        ['name', 'unit']
    ).sum().astype(int).reset_index().to_dict('records') if foods else []

    return day


def aggregate(data):
    if not data['days']:
        data['days'] = []
    else:
        number_days = len(data['days'])

        if number_days == 1:
            data['days'] = [_aggregate_day(data['days'][0])]
        else:
            with pathos.multiprocessing.ProcessPool() as pool:
                data['days'] = list(pool.imap(_aggregate_day, data['days']))

            data['aggregation'] = {
                'goals': {
                    key: {
                        'unit': data['days'][0]['goals'][key]['unit'],
                        
                        ##### ORIGINAL LINE #####
                        'quantity': round(_mean(day['goals'][key]['quantity'] for day in data['days']))
                        
                        ##### MODIFIED LINE #####
                        # 'quantity': round(_mean(day['goals'][key]['quantity'] for day in data['days'] if day['totals'][key]['quantity']))
                        #####
                        
                        #'quantity': round(_mean(day['goals'][key] for day in data['days']))

                    } for key in data['days'][0]['goals'].keys()
                },
                'totals': {
                    key: {
                        'unit': data['days'][0]['totals'][key]['unit'],
                        #'quantity': round(_mean(day['totals'][key] for day in data['days']))
                        
                        ##### ORIGINAL LINE #####
                        'quantity': round(_mean(day['totals'][key]['quantity'] for day in data['days']))
                        
                        ##### MODIFIED LINE #####
                        # 'quantity': round(_mean(day['totals'][key]['quantity'] for day in data['days'] if day['totals'][key]['quantity']))
                        #####
                        
                    } for key in data['days'][0]['goals'].keys()
                },
                'meals': []
            }


            for meal_id in range(len(data['days'][0]['meals'])):
                foods = [food for day in data['days'] for food in day['meals'][meal_id]['foods']]

                data['aggregation']['meals'] += [{
                    'totals': {
                        key: {
                            'unit': data['days'][0]['meals'][meal_id]['totals'][key]['unit'],
                            'quantity': round(
                                #_mean(day['meals'][meal_id][key] for day in data['days'])
                                _mean(day['meals'][meal_id]['totals'][key]['quantity'] for day in data['days'])
                            )
                        } for key in data['days'][0]['goals'].keys()
                    },
                    'foods': pandas.DataFrame(foods).groupby(
                        ['name', 'unit']
                    ).sum().div(number_days).astype(int).reset_index().to_dict('records') if foods else []
                }]

                foods = [food for meal in data['aggregation']['meals'] for food in meal['foods']]
                data['aggregation']['foods'] = pandas.DataFrame(foods).groupby(
                    ['name', 'unit']
                ).sum().astype(int).reset_index().to_dict('records') if foods else []

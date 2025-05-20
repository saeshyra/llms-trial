from statsmodels.tsa.stattools import adfuller
from communication_layer.text_formatter import TextFormatterUtility
import numpy


def prepare_data(raw_data, communicator):
    tf = TextFormatterUtility()
    if raw_data == "empty" or raw_data == "missing_data_excess":
        return raw_data
    data = {}
    data['username'] = raw_data['user_name']
    data['keys'] = raw_data['keys']
    data['up_thr'] = 100 + raw_data['threshold']
    data['lo_thr'] = 100 - raw_data['threshold']
    data['consequences'] = raw_data['consequences']

    data['fst_day'] = communicator.wordify_date(raw_data['days'][0]['day_id'])
    data['lst_day'] = communicator.wordify_date(raw_data['days'][-1]['day_id'])
    data['day_n'] = len(raw_data['days'])
    data['day_word'] = 'days' if data['day_n'] > 1 else 'day'
    data['diet'] = {}
    data['unk_keys'] = []

    aggregated_data = raw_data['aggregation'] if 'aggregation' in raw_data.keys() else raw_data['days'][0]

    for key in data['keys']:
        try:
            data['diet'].update({key:
                                     {'goal_perc': aggregated_data['budget'][key]['goal_percentage'],
                                      'is_almost_ok': tf.is_almost_ok(aggregated_data['budget'][key]['goal_percentage'],
                                                                      tf.thresholds['val']),
                                      'unit': aggregated_data['budget'][key]['unit'],
                                      'quantity': aggregated_data['budget'][key]['quantity'],
                                      'dist': aggregated_data['budget'][key]['distance'],
                                      'significant': True if aggregated_data['budget'][key]['distance'] > raw_data[
                                          'threshold'] else False,
                                      'std_dev': aggregated_data['budget'][key]['standard_deviation'] if 'standard_deviation' in aggregated_data['budget'][key].keys() else 0,
                                      'more_less': 'more' if aggregated_data['budget'][key]['goal_percentage'] >data['up_thr']
                                                          else ('less' if aggregated_data['budget'][key]['goal_percentage'] < data['lo_thr']else 'ok'),

                                      'category': 'excess' if aggregated_data['budget'][key][
                                                                  'goal_percentage'] > 100
                                      else 'missing' if aggregated_data['budget'][key]['goal_percentage'] < 100
                                      else 'balance',
                                      'foods': list(map(lambda food: {'name': food['name'],
                                                                     'val': food['totals'][key]['quantity'],
                                                                     'perc': food['totals'][key]['total_percentage'],
                                                                     'unit': food['totals'][key]['unit']},
                                                       [f for f in sorted(aggregated_data['foods'],
                                                                          key=lambda x: x['totals'][key]['total_percentage'],
                                                                          reverse=True)]
                                                       )
                                                   ) if aggregated_data['foods'] else [],
                                      'worst_day': (list(map(lambda day: {'day': communicator.wordify_date(day['day_id']),
                                                                         'goal_perc': day['budget'][key]['goal_percentage'],
                                                                         'dist': day['budget'][key]['distance'],
                                                                         'more_less': 'more' if day['budget'][key][
                                                                                                   'goal_percentage'] > 100 else 'less',
                                                                         'category': 'excess' if day['budget'][key][
                                                                                                      'goal_percentage'] > 100 else 'missing',
                                                                         'significant': True if day['budget'][key][
                                                                                                    'distance'] >= raw_data[
                                                                                                    'threshold'] else False,
                                                                         'is_almost_ok': tf.is_almost_ok(day['budget'][key]['goal_percentage'], tf.thresholds['val'])},
                                                            [d for d in sorted(raw_data['days'],
                                                                               key=lambda x: x['budget'][key]['distance'],
                                                                               reverse=True)]
                                                            )
                                                        )[0]) if data['day_n'] >= 2 else None,
                                      'trend_direction' : ('+' if numpy.polyfit(range(len(raw_data['days'])), [el['budget'][key]['goal_percentage'] for el in raw_data['days']], 1)[0]>0 else '-') if data['day_n'] >= 3 else None,
                                      'trend_dir_intense' : (True if numpy.polyfit(range(len(raw_data['days'])), [el['budget'][key]['goal_percentage'] for el in raw_data['days']], 1)[0]>10 else False) if data['day_n']>=3 else None
                                      }
                                 })
        except KeyError:
            data.update({'unk_keys': data['unk_keys']+[key]})
            continue

        #if the sample size is too short we can't assume anything about the stationary nature of data, must handle this case in the template
        try:
            data['diet'][key].update({'stationary' : (True if adfuller([el['budget'][key]['goal_percentage'] for el in raw_data['days']])[1] <= 0.05 else False) if data['day_n']>=3 else None})
        except:
            data['diet'][key].update({'stationary' : None})

        if ('energy' in data['keys'] and len(data['keys'])) > 1 or ('energy' not in data['keys'] and len(data['keys']) >= 1):
            data['nutrients_available'] = True
    # print('data:', data)
    return data

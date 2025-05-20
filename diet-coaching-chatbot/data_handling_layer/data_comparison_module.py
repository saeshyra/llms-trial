def compare(data):
    less = (data['less_recent'].get('aggregation', data['less_recent']['days'][0])['budget'])
    more = (data['more_recent'].get('aggregation', data['more_recent']['days'][0])['budget'])

    data['comparison'] = {
        key: {'trend': less[key]['distance'] - more[key]['distance']} for key in less.keys()
    }

    if 'aggregation' in data['less_recent'] and 'aggregation' in data['more_recent']:
        for key in less.keys():
            data['comparison'][key]['regular'] = less[key]['standard_deviation'] - more[key]['standard_deviation']


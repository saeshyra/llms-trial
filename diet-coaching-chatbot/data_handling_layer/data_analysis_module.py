import statistics


def _total_percentage(data, day_totals):
    for key in day_totals.keys():
        data[key]['total_percentage'] = round(
            data[key]['quantity'] * 100 / (day_totals[key]['quantity'] or 1)
            #data[key] * 100 / (day_totals[key] or 1)
        )

def _meal_percentage(data, meal_totals):
    for key in meal_totals.keys():
        data[key]['meal_percentage'] = round(
            data[key]['quantity'] * 100 / (meal_totals[key]['quantity'] or 1)
            #data[key] * 100 / (meal_totals[key] or 1)
        )


def _energy_percentage(data, energy):
    for key in energy.keys():
        
        ##### ORIGINAL #####
        data[key]['energy_percentage'] = round(
            data[key]['quantity'] * energy[key] / (data['energy']['quantity'] or 1)
            #data[key] * energy[key] / (data['calories'] or 1)
        )
        
        ##### MODIFIED #####
        # if data[key]['quantity']:
        #     data[key]['energy_percentage'] = round(
        #         data[key]['quantity'] * energy[key] / (data['energy']['quantity'] or 1)
        #         #data[key] * energy[key] / (data['calories'] or 1)
        #     )
        #####


def _analyse_food(food, energy, day_totals, meal_totals=None):
    food['totals'] = {}

    for key in day_totals.keys():
        food['totals'][key] = {
            'unit': day_totals[key]['unit'],
            'quantity': food.pop(key)
        }

    _total_percentage(food['totals'], day_totals)

    if meal_totals:
        _meal_percentage(food['totals'], meal_totals)

    _energy_percentage(food['totals'], energy)


def _analyse_day(day, energy):
    _energy_percentage(day['goals'], energy)
    _energy_percentage(day['totals'], energy)

    ##### ORIGINAL
    day['budget'] = {
        key: {
            'unit': day['goals'][key]['unit'],
            'quantity': day['goals'][key]['quantity'] - day['totals'][key]['quantity'],
            'goal_percentage': round(
                day['totals'][key]['quantity'] * 100 / (day['goals'][key]['quantity'] or 1)
                #day['totals'][key] * 100 / (day['goals'][key] or 1)
            ),
            'distance': round(
                abs(100 - day['totals'][key]['quantity'] * 100 / (day['goals'][key]['quantity'] or 1))
                #abs(100 - day['totals'][key] * 100 / (day['goals'][key] or 1))
            )
        } for key in day['goals'].keys()
    }
    
    ##### MODIFIED #####
    # day['budget'] = {
    #     key: {
    #         'unit': day['goals'][key]['unit'],
    #         'quantity': day['goals'][key]['quantity'] - day['totals'][key]['quantity'] if day['totals'][key]['quantity'] else None,
    #         'goal_percentage': round(
    #             day['totals'][key]['quantity'] * 100 / (day['goals'][key]['quantity'] or 1)
    #             #day['totals'][key] * 100 / (day['goals'][key] or 1)
    #         ) if day['totals'][key]['quantity'] else None,
    #         'distance': round(
    #             abs(100 - day['totals'][key]['quantity'] * 100 / (day['goals'][key]['quantity'] or 1))
    #             #abs(100 - day['totals'][key] * 100 / (day['goals'][key] or 1))
    #         ) if day['totals'][key]['quantity'] else None
    #     } for key in day['goals'].keys()
    # }
    #####

    ##### ORIGINAL #####
    day['budget'] = {
        'energy': day['budget'].pop('energy'),
        #'calories': day['budget'].pop('calories')
        **dict(sorted(day['budget'].items(), key=lambda item: item[1]['goal_percentage'], reverse=True))
    }
    
    ##### MODIFIED #####
    # day['budget'] = {
    #     'energy': day['budget'].pop('energy'),
    #     #'calories': day['budget'].pop('calories')
    #     **dict(sorted({item for item in day['budget'].items() if item[1]['goal_percentage']}, key=lambda item: item[1]['goal_percentage'], reverse=True))
    # }
    #####

    for meal in day['meals']:
        _total_percentage(meal['totals'], day['totals'])
        _energy_percentage(meal['totals'], energy)

        for food in meal['foods']:
            _analyse_food(food, energy, day['totals'], meal['totals'])

    for food in day['foods']:
        _analyse_food(food, energy, day['totals'])


def analyse(data):
    if data['days'][0]['goals']['energy']['unit'] == 'kcal':
        energy = {'fat': 900, 'carbohydrates': 400, 'sugar': 400, 'protein': 400} #ref value: kcal per 100g of said nutrient
    else:
        energy = {'fat': 900 * 4.184, 'carbohydrates': 400 * 4.184, 'sugar': 400 * 4.184, 'protein': 400 * 4.184}
    #energy = {'fat': 900, 'carbohydrates': 400, 'sugar': 400, 'protein': 400} #ref value: kcal per 100g of said nutrient

    for day in data['days']:
        _analyse_day(day, energy)

    if 'aggregation' in data:
        _analyse_day(data['aggregation'], energy)

        for key in data['aggregation']['goals'].keys():
            
            ##### ORIGINAL #####
            data['aggregation']['budget'][key]['standard_deviation'] = round(
                statistics.stdev([day['budget'][key]['goal_percentage'] for day in data['days']])
            )
            
            ##### MODIFIED #####
            # data['aggregation']['budget'][key]['standard_deviation'] = round(
            #     statistics.stdev([day['budget'][key]['goal_percentage'] for day in data['days'] if day['budget'][key]['goal_percentage']])
            # )
            #####

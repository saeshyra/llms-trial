import datetime
import numpy
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

fe = fm.FontEntry(
    fname='/stable/NotoSans-Regular.ttf',
    name='Noto Sans')
fm.fontManager.ttflist.insert(0, fe) # or append is fine
plt.rcParams['font.family'] = fe.name

from communication_layer.communicator import Communicator
from communication_layer.text_formatter import TextFormatterUtility

communicator = Communicator()
textf = TextFormatterUtility()

color_schemes = {
    'thresholds': {
        'upper': '#c20000',
        'lower': 'gold',
        'balance': 'limegreen',
    },
    'line': {
        'data': ['#023e8a','mediumpurple'],
        'trend': ['#023e8a','mediumpurple'],
    },
    'pie': {
        'data': {'outer': ['#160765','#382181','#573A9E','#7555BC','#9370DB','#ad95de','#d5c3fa'], #after
                 'inner': ["#023e8a","#0077b6","#0096c7","#00b4d8","#48cae4","#90e0ef","#ade8f4"]} #before
    },
    'most_off_plan': {
        'before': 'orangered',
        'after': 'darkred'
    }
}


def line_chart(percentages, thresholds, data, key, quantify=False):
    data_colors = iter(color_schemes['line']['data'])
    trend_colors = iter(color_schemes['line']['trend'])
    most_off_plan_colors = color_schemes['most_off_plan']
    periods = iter(['before','after'])

    full_perc_list = []
    for l in percentages:
        for el in l:
            full_perc_list.append(el)

    if thresholds>=5:
        full_perc_list += [100 + thresholds]

    quarters = [0]
    while quarters[-1] < max(full_perc_list):
        quarters.append(quarters[-1] + 25)
    # quarters.append(quarters[-1] + 25)

    for perc_list in percentages:
        data_color = next(data_colors)
        trend_color = next(trend_colors)
        period = next(periods)
        xarray = range(len(perc_list))
        y_distance = [abs(x-100) for x in perc_list]
        max_distance = max(y_distance)
        y_distance = list(map(lambda x : 0 if x!= max_distance else x, y_distance))
        x_distance = xarray[y_distance.index(max_distance)]
        y_distance = perc_list[x_distance]
        midpoint = (xarray[0]+xarray[-1])/2

        plt.axhline(100, color=color_schemes['thresholds']['balance'], linestyle='--')
        plt.plot(xarray, perc_list, color=data_color, marker='o', mfc=data_color, mec='black', label = f'Your daily {key} intake '+(period if len(percentages)>1 else ''), zorder=1)
        if len(xarray)>1:
            plt.scatter(x_distance, y_distance, color=most_off_plan_colors[period], marker='s', edgecolors='black', label = f'The toughest day '+(period if len(percentages)>1 else ''),zorder=2)

        if len(percentages) > 1:
            before = data['less_recent']
            after = data['more_recent']
            xlabel = f'From {before["fst_day"]} to {before["lst_day"]} \nVS\nFrom {after["fst_day"]} to {after["lst_day"]}'
        else:
            xlabel = f'From {data["fst_day"]} to {data["lst_day"]}'
        plt.xlabel(xlabel)
        plt.xticks([])
        plt.ylabel('%', rotation=0, labelpad=10)
        if quantify:
            print('yticks:', quarters, [textf.quantify(el, thresholds_key='val', postfix=True, compare_to_goal=True) for el in quarters])
            plt.yticks(quarters, [textf.quantify(el, thresholds_key='val', postfix=True, compare_to_goal=True) for el in quarters])
        else:
            plt.yticks(range(0, quarters[-1], 10))

    if thresholds>=5:
        plt.axhline(100 - thresholds, color=color_schemes['thresholds']['lower'], linestyle='--', label=('You shouldn\'t be below this ' if quantify else 'Deficit tolerance'))
        plt.axhline(100 + thresholds, color=color_schemes['thresholds']['upper'], linestyle='--', label=('You shouldn\'t be above this ' if quantify else 'Excess tolerance'))
    plt.axhline(100, color=color_schemes['thresholds']['balance'], linestyle='--')

    title = f'Your {key} intake:'
    plt.title(title)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    img = plt.imread(f'data_handling_layer/emojis/{key}.png')
    fig = plt.gcf()
    fig.figimage(img, xo=fig.bbox.xmax - 0.8 * img.shape[1], yo=fig.bbox.ymax - 2 * img.shape[0])
    
    plot = plt.gcf()
    plt.close(plot)

    return plot

def trend_chart(percentages, thresholds, key, data, quantify=False):
    trend_colors = iter(color_schemes['line']['trend'])
    periods = iter(['before','after'])

    full_list = []
    for l in percentages:
        for el in l:
            full_list.append(el)

    quarters = [0]
    while quarters[-1] < max(full_list):
        quarters.append(quarters[-1] + 25)
    quarters.append(quarters[-1] + 25)

    for perc_list in percentages:
        trend_color = next(trend_colors)
        period = next(periods)
        xarray = range(len(perc_list))
        midpoint = (xarray[0]+xarray[-1])/2

        if len(xarray) > 2:
            trend = numpy.poly1d(numpy.polyfit(xarray, perc_list, 1))
            plt.plot([xarray[0],xarray[int((len(xarray)-1)/2)],xarray[-1]], trend([xarray[0],xarray[int((len(xarray)-1)/2)],xarray[-1]]), color=trend_color, marker= '>', label = f'Your {key} trend '+(period if len(percentages)>1 else ''))
            plt.ylim(ymin=0)
        else:
            return "*There's not enough data to get the trend chart*"

        if len(percentages) > 1:
            before = data['less_recent']
            after = data['more_recent']
            xlabel = f'From {before["fst_day"]} to {before["lst_day"]} \nVS\nFrom {after["fst_day"]} to {after["lst_day"]}'
        else:
            xlabel = f'From {data["fst_day"]} to {data["lst_day"]}'
        plt.xlabel(xlabel)
        plt.xticks([])
        plt.ylabel('%', rotation=0, labelpad=10)
        if quantify:
            plt.yticks(quarters, [textf.quantify(el, thresholds_key='val', postfix=True, compare_to_goal=True) for el in quarters])
        else:
            plt.yticks(range(0, quarters[-1], 10))

    if thresholds >= 5:
        plt.axhline(100 - thresholds, color=color_schemes['thresholds']['lower'], linestyle='--', label=('You shouldn\'t be below this ' if quantify else 'Deficit tolerance'))
        plt.axhline(100 + thresholds, color=color_schemes['thresholds']['upper'], linestyle='--', label=('You shouldn\'t be above this ' if quantify else 'Excess tolerance'))
    plt.axhline(100, color=color_schemes['thresholds']['balance'], linestyle='--')

    title = f'Your {key} trend:'
    plt.title(title)
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    img = plt.imread(f'data_handling_layer/emojis/{key}.png')
    fig = plt.gcf()
    fig.figimage(img, xo=fig.bbox.xmax - 0.8 * img.shape[1], yo=fig.bbox.ymax - 2 * img.shape[0])
    
    plot = plt.gcf()
    plt.close(plot)

    return plot



def _barh_table(percentages, labels, units, totals, goals, threshold, title):
    barh_table, (barh, table) = plt.subplots(2)
    colors = ['gold' if p < 100 - threshold else 'tomato' if p > 100 + threshold else 'limegreen' for p in percentages]
    barh.axvline(100 - threshold, color='gold')
    barh.axvline(100 + threshold, color='tomato')
    barh.axvline(100, color='limegreen')
    barh.barh(labels, percentages, 0.25, color=colors)
    barh.set_xlabel('%')
    barh.set_xticks(range(0, max(100 + threshold, max(percentages)) + 10, 10))
    table.axis('off')
    table.table(
        [[total, goal, goal - total] for total, goal in zip(totals, goals)],
        cellLoc='center',
        cellColours=[[c] * 3 for c in reversed(colors)],
        rowLabels=[f'{label} ({units[label_id]})' for label_id, label in enumerate(reversed(labels))],
        rowColours=['peachpuff'] * len(labels),
        rowLoc='center',
        colLabels=['Total', 'Goal', 'Remaining'],
        colColours=['peachpuff'] * 3,
        loc=(0, 0)
    )
    plt.suptitle(title)
    plt.close(barh_table)

    return barh_table


def food_chart(foods_lists, key, quantify=False):
    plt.rcParams['axes.titlepad'] = 7
    rings = iter(['outer','inner']) if len(foods_lists)>1 else iter(['inner'])
    periods = iter(['after', 'before'])
    maximum_total_contribution = 75
    minimum_single_contribution = 2
    maximum_contribution_n = 6
    radius = 1.6
    width = 0.5
    pctdistance = iter([1.15, 0.5])
    locs = [(0.95, 0.55),(0.95, 0.05)] # legends locations
    labels = [] # foods with values
    pies = []  # pie charts backups
    fig, ax = plt.subplots()


    for food_list in foods_lists:
        donut_colors = color_schemes['pie']['data'][next(rings)]
        radius -= 0.3
        width -= 0.1

        # if sum(percentages) > 1: #remember to handle this
        foods = sorted(food_list, key=lambda item: item['val'], reverse=True)

        if sum([f['perc'] for f in foods]) > maximum_total_contribution or len(foods) > maximum_contribution_n:
            up_to_max = []
            index = (numpy.cumsum([f['perc'] for f in foods]) <= maximum_total_contribution).argmin()
            if index == 0:
                index = min(len(foods), maximum_contribution_n)
            up_to_max = foods[:index+1]
            if len(up_to_max) > maximum_contribution_n:
                up_to_max = up_to_max[:maximum_contribution_n-1]
            lower_than_thresh = list(filter(lambda x: x['perc'] < minimum_single_contribution, up_to_max))
            up_to_max = list(filter(lambda v: v not in lower_than_thresh, up_to_max))
            if len(up_to_max) < len(foods):
                other_foods = list(filter(lambda v: v not in up_to_max, foods))
                foods = up_to_max + [{'name': 'Everything else you ate',
                                    'val':  sum(f['val'] for f in other_foods),
                                    'perc': sum(f['perc'] for f in other_foods),
                                    'unit': other_foods[-1]['unit']}]
            
        percentages = [f['perc'] for f in foods]
        quantities = [f['val'] for f in foods]
        unit = foods[-1]['unit']


        if len(foods) < 7: #(6 + "others")
            last_color = donut_colors[-1]
            donut_colors = donut_colors[:(len(foods)-1)]+[last_color]

        # First Ring is outside
        ax.axis('equal')
        slice_labels = '%1.0f%%' #lambda pct: '{:.0f}%'.format(round(pct)) if round(pct) > 4 else ''
        if quantify:
            slice_labels = lambda pct: ''
        pie = ax.pie(percentages,
                     radius=radius,
                     colors= donut_colors[:len(foods)],
                     autopct = slice_labels,
                     pctdistance= next(pctdistance),
                     startangle=-90,
                     counterclock=False,
                     wedgeprops={'lw': 0.5, 'width': 0.25})[0]

        plt.setp(pie, width=width, edgecolor='white')
        pies.append(pie)

        plt.margins(0, 0)

        labels.append([f'{t[0]} ({t[1]} {unit})' for t in zip([f['name'] for f in foods], quantities)])

        #plt.title(f'Food that mostly impacted on your {key} intake \n', y=1.08)

    legend1 = plt.legend(pies[0], labels[0], loc='center left', bbox_to_anchor=(1, 0.5), title=f'Food that gave you most {key} {next(periods)+": " if len(foods_lists)>1 else ": "}')
    if len(foods_lists) > 1:
        plt.legend(pies[1], labels[1], loc='center left', bbox_to_anchor=(1, 1.0), title=f'Food that gave you most {key} {next(periods)+": " if len(foods_lists)>1 else ": "}')
        plt.gca().add_artist(legend1)
        
    # add nutrient emoji in the center
    img = plt.imread(f'data_handling_layer/emojis/{key}.png')
    fig.figimage(img, xo=fig.bbox.xmax / 2 - 1.4 * img.shape[1], yo=fig.bbox.ymax / 2 - 0.8 * img.shape[0])

    pie = plt.gcf()
    plt.close(pie)

    return pie


def _visualize_day(day, day_title, keys, threshold, meal_names):
    day['goals']['chart'] = food_chart(
        [
            day['goals']['fat']['energy_percentage'],
            day['goals']['carbohydrates']['energy_percentage'],
            day['goals']['protein']['energy_percentage']
        ],
        ['Fat', 'carbohydrates', 'Protein'],
        [
            day['goals']['fat']['quantity'],
            day['goals']['carbohydrates']['quantity'],
            day['goals']['protein']['quantity']
        ],
        day['goals']['fat']['unit'],
        f'''{day_title} | Goals Energy'''
    )

    day['totals']['chart'] = food_chart(
        [
            day['totals']['fat']['energy_percentage'],
            day['totals']['carbohydrates']['energy_percentage'],
            day['totals']['protein']['energy_percentage']
        ],
        ['Fat', 'carbohydrates', 'Protein'],
        [
            day['totals']['fat']['quantity'],
            day['totals']['carbohydrates']['quantity'],
            day['totals']['protein']['quantity']
        ],
        day['totals']['fat']['unit'],
        f'''{day_title} | Totals Energy'''
    )

    for meal_id, meal in enumerate(day['meals']):
        meal['totals']['chart'] = food_chart(
            [
                meal['totals']['fat']['energy_percentage'],
                meal['totals']['carbohydrates']['energy_percentage'],
                meal['totals']['protein']['energy_percentage']
            ],
            ['Fat', 'carbohydrates', 'Protein'],
            [
                meal['totals']['fat']['quantity'],
                meal['totals']['carbohydrates']['quantity'],
                meal['totals']['protein']['quantity']
            ],
            meal['totals']['fat']['unit'],
            f'''{day_title} | "{meal_names[meal_id]}" Energy'''
        )

        for key in keys:
            meal['totals'][key]['chart'] = food_chart(
                [food['totals'][key]['meal_percentage'] for food in meal['foods']],
                [f'''{food['name']}, {food['quantity']} {food['unit']}''' for food in meal['foods']],
                [food['totals'][key]['quantity'] for food in meal['foods']],
                meal['totals'][key]['unit'],
                f'''{day_title} | {key.capitalize()} from "{meal_names[meal_id]}" Foods'''
            )

    for food in day['foods']:
        food['totals']['chart'] = food_chart(
            [
                food['totals']['fat']['energy_percentage'],
                food['totals']['carbohydrates']['energy_percentage'],
                food['totals']['protein']['energy_percentage']
            ],
            ['Fat', 'carbohydrates', 'Protein'],
            [
                food['totals']['fat']['quantity'],
                food['totals']['carbohydrates']['quantity'],
                food['totals']['protein']['quantity']
            ],
            food['totals']['fat']['unit'],
            f'''{food['name']}, {food['quantity']} {food['unit']} Energy'''
        )

    for key in keys:
        day['totals'][key]['chart'] = {
            'meals': food_chart(
                [meal['totals'][key]['total_percentage'] for meal in day['meals']],
                meal_names,
                [meal['totals'][key]['quantity'] for meal in day['meals']],
                day['totals'][key]['unit'],
                f'''{day_title} | {key.capitalize()} from All Meals'''
            ),
            'foods': food_chart(
                [food['totals'][key]['total_percentage'] for food in day['foods']],
                [f'''{food['name']}, {food['quantity']} {food['unit']}''' for food in day['foods']],
                [food['totals'][key]['quantity'] for food in day['foods']],
                day['totals'][key]['unit'],
                f'''{day_title} | {key.capitalize()} from All Foods'''
            )
        }

    day['budget']['chart'] = _barh_table(
        [day['budget'][key]['goal_percentage'] for key in reversed(day['budget'].keys())],
        [key.capitalize() for key in reversed(day['budget'].keys())],
        [day['goals'][key]['unit'] for key in day['budget'].keys()],
        [day['totals'][key]['quantity'] for key in day['budget'].keys()],
        [day['goals'][key]['quantity'] for key in day['budget'].keys()],
        threshold,
        f'''{day_title} | Goals Achievement'''
    )


def visualize(data, keys, threshold, meal_names):
    if len(data['days']) == 1:
        print('visualize day')
        _visualize_day(
            data['days'][0],
            datetime.date.fromisoformat(data['days'][0]['day_id']).strftime("%d %B %Y"),
            keys,
            threshold,
            meal_names
        )
    elif 'aggregation' in data:
        print('aggregation')
        day_title = f'''From {
        datetime.date.fromisoformat(data['days'][0]['day_id']).strftime('%d %B %Y')
        } to {
        datetime.date.fromisoformat(data['days'][-1]['day_id']).strftime('%d %B %Y')
        }'''
        _visualize_day(data['aggregation'], day_title, keys, threshold, meal_names)

        for key in keys:
            data['aggregation']['budget'][key]['chart'] = line_chart(
                [day['budget'][key]['goal_percentage'] for day in data['days']],
                threshold,
                f'{key.capitalize()} Goal Achievement',
                day_title
            )

import data_handling_layer
import datetime


if __name__ == '__main__':
    user_name = ''
    password = ''

    dates = {}

    date_delta = 1 * 2
    less_recent = [datetime.date.today() - datetime.timedelta(d + date_delta) for d in range(date_delta)]
    less_recent.reverse()

    update = data_handling_layer.update(user_name, password, less_recent, ['carbohydrates', 'protein', 'sodium'])

    date_delta = 1 * 2
    more_recent = [datetime.date.today() - datetime.timedelta(d) for d in range(date_delta)]
    more_recent.reverse()

    compare = data_handling_layer.compare(user_name, password, less_recent, more_recent, ['energy', 'fat', 'sugar'])

    # import json
    # json_dump = json.dumps(compare, indent='\t', ensure_ascii=False)
    # print(json_dump)
    # with open('data.json', 'w') as file:
    #     file.write(json_dump)

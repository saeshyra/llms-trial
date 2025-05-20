import user_profiling_layer


if __name__ == '__main__':
    user_name = 'test_phil_diet1'

    preferences = user_profiling_layer.dumps(user_name)

    preferences['threshold'] = 5
    preferences['report_hour'] = 9

    if 'carbohydrates' in preferences['keys']:
        preferences['keys'].remove('carbohydrates')

    if 'sugar' in preferences['keys']:
        preferences['keys'].remove('sugar')

    user_profiling_layer.loads(preferences)

    # import json
    # json_dump = json.dumps(preferences, indent='\t', ensure_ascii=False)
    # print(json_dump)
    # with open('preferences.json', 'w') as file:
    #     file.write(json_dump)

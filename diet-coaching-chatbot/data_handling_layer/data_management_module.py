import mysql.connector
import sys

def db_read_days(user, energy_unit, days):
    days_dump = []

    day_query = '''
        SELECT 
            energy_goal, fat_goal, carbohydrates_goal, sugar_goal, protein_goal, sodium_goal, total_energy, total_fat, 
            total_carbohydrates, total_sugar, total_protein, total_sodium
        FROM day WHERE user = %s AND id = %s;
    '''

    meal_query = '''
        SELECT id, energy, fat, carbohydrates, sugar, protein, sodium 
        FROM meal WHERE user = %s AND day = %s ORDER BY id;
    '''

    food_query = '''
        SELECT meal, name, unit, quantity, energy, fat, carbohydrates, sugar, protein, sodium 
        FROM food WHERE user = %s AND day = %s ORDER BY meal, id;
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                for day in days:
                    cursor.execute(day_query, [user, day])
                    day_row = cursor.fetchone()

                    cursor.execute(meal_query, [user, day])
                    meal_rows = cursor.fetchall()

                    cursor.execute(food_query, [user, day])
                    food_rows = cursor.fetchall()
                    days_dump += [{
                        'day_id': day,
                        'goals': {
                            'energy': {
                                'unit': 'kcal' if energy_unit == 'calories' else 'kJ',
                                'quantity': day_row[0]
                            },
                            'fat': {'unit': 'g', 'quantity': day_row[1]},
                            'carbohydrates': {'unit': 'g', 'quantity': day_row[2]},
                            'sugar': {'unit': 'g', 'quantity': day_row[3]},
                            'protein': {'unit': 'g', 'quantity': day_row[4]},
                            'sodium': {'unit': 'mg', 'quantity': day_row[5]}
                        },
                        'totals': {
                            'energy': {
                                'unit': 'kcal' if energy_unit == 'calories' else 'kJ',
                                'quantity': day_row[6]
                            },
                            'fat': {'unit': 'g', 'quantity': day_row[7]},
                            'carbohydrates': {'unit': 'g', 'quantity': day_row[8]},
                            'sugar': {'unit': 'g', 'quantity': day_row[9]},
                            'protein': {'unit': 'g', 'quantity': day_row[10]},
                            'sodium': {'unit': 'mg', 'quantity': day_row[11]}
                        },
                        'meals': [{
                            'totals': {
                                'energy': {
                                    'unit': 'kcal' if energy_unit == 'calories' else 'kJ',
                                    'quantity': meal_row[1]
                                },
                                'fat': {'unit': 'g', 'quantity': meal_row[2]},
                                'carbohydrates': {'unit': 'g', 'quantity': meal_row[3]},
                                'sugar': {'unit': 'g', 'quantity': meal_row[4]},
                                'protein': {'unit': 'g', 'quantity': meal_row[5]},
                                'sodium': {'unit': 'mg', 'quantity': meal_row[6]}
                            },
                            'foods': [{
                                'name': food_row[1],
                                'unit': food_row[2],
                                'quantity': food_row[3],
                                'energy': food_row[4],
                                'fat': food_row[5],
                                'carbohydrates': food_row[6],
                                'sugar': food_row[7],
                                'protein': food_row[8],
                                'sodium': food_row[9]
                            } for food_row in food_rows if food_row[0] == meal_row[0]]
                        } for meal_row in meal_rows]
                    }]

    except mysql.connector.Error as error:
        print(error, file=sys.stderr)

    return days_dump


def db_read_user_prefs(user):
    user_dump = {}

    user_query = 'SELECT * FROM user WHERE name = %s;'

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                keys = ['energy', 'fat', 'carbohydrates', 'sugar', 'protein', 'sodium']
                cursor.execute(user_query, [user])
                user_row = cursor.fetchone()

                user_dump = {
                    'user_name': user_row[0],
                    'low_numeracy': bool(user_row[1]),
                    'consequences': bool(user_row[2]),
                    'report_day': user_row[3],
                    'report_hour': user_row[4],
                    'threshold': user_row[5],
                    'keys': [keys[key_id] for key_id, report in enumerate(user_row[6:12]) if report],
                    'energy_unit': user_row[13],
                    'meal_names': [meal_name for meal_name in user_row[14:] if meal_name],
                }

    except mysql.connector.Error as error:
        print(error, file=sys.stderr)

    return user_dump


def db_write_days(user, energy_unit, days_dump):

    day_query = '''
        INSERT INTO day (
            user, id, energy_goal, fat_goal, carbohydrates_goal, sugar_goal, protein_goal, sodium_goal, total_energy, 
            total_fat, total_carbohydrates, total_sugar, total_protein, total_sodium
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            energy_goal = VALUES(energy_goal), fat_goal = VALUES(fat_goal), 
            carbohydrates_goal = VALUES(carbohydrates_goal), sugar_goal = VALUES(sugar_goal), 
            protein_goal = VALUES(protein_goal), sodium_goal = VALUES(sodium_goal), total_energy = VALUES(total_energy), 
            total_fat = VALUES(total_fat), total_carbohydrates = VALUES(total_carbohydrates), 
            total_sugar = VALUES(total_sugar), total_protein = VALUES(total_protein), 
            total_sodium = VALUES(total_sodium);
    '''

    meal_delete_query = 'DELETE FROM meal WHERE user = %s AND id >= %s;'

    meal_insert_query = '''
        INSERT INTO meal (
            user, day, id, energy, fat, carbohydrates, sugar, protein, sodium
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            energy = VALUES(energy), fat = VALUES(fat), carbohydrates = VALUES(carbohydrates), sugar = VALUES(sugar), 
            protein = VALUES(protein), sodium = VALUES(sodium);
    '''

    food_delete_query = 'DELETE FROM food WHERE user = %s AND day = %s;'

    food_insert_query = '''
        INSERT INTO food (
            user, day, meal, id, name, unit, quantity, energy, fat, carbohydrates, sugar, protein, sodium
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    day_query,
                    [
                        [
                            user, day['day_id'], day['goals'].get(energy_unit, 0), day['goals'].get('fat', 0),
                            day['goals'].get('carbohydrates', 0), day['goals'].get('sugar', 0),
                            day['goals'].get('protein', 0), day['goals'].get('sodium', 0),
                            day['totals'].get(energy_unit, 0), day['totals'].get('fat', 0),
                            day['totals'].get('carbohydrates', 0), day['totals'].get('sugar', 0),
                            day['totals'].get('protein', 0), day['totals'].get('sodium', 0)
                        ] for day in days_dump
                    ]
                )

                cursor.execute(meal_delete_query, [user, len(days_dump[0]['meals'])])
                cursor.executemany(
                    meal_insert_query,
                    [
                        [
                            user, day['day_id'], meal_id, meal.get(energy_unit, 0), meal.get('fat', 0),
                            meal.get('carbohydrates', 0), meal.get('sugar', 0), meal.get('protein', 0),
                            meal.get('sodium', 0)
                        ] for day in days_dump for meal_id, meal in enumerate(day['meals'])
                    ]
                )

                cursor.executemany(food_delete_query, [[user, day['day_id']] for day in days_dump])
                cursor.executemany(
                    food_insert_query,
                    [
                        [
                            user, day['day_id'], meal_id, food_id, food['name'], food['unit'], food['quantity'],
                            food.get(energy_unit, 0), food.get('fat', 0), food.get('carbohydrates', 0),
                            food.get('sugar', 0), food.get('protein', 0), food.get('sodium', 0)
                        ]
                        for day in days_dump
                        for meal_id, meal in enumerate(day['meals'])
                        for food_id, food in enumerate(meal['foods'])
                    ]
                )

                connection.commit()

    except Exception as error:
        print(error)


def db_write_user(user_dump):
    user_query = '''
        INSERT INTO user (
            name, energy_unit, meal_name0, meal_name1, meal_name2, meal_name3, meal_name4, meal_name5
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
        ON DUPLICATE KEY UPDATE 
            energy_unit = VALUES(energy_unit), meal_name0 = VALUES(meal_name0), meal_name1 = VALUES(meal_name1), 
            meal_name2 = VALUES(meal_name2), meal_name3 = VALUES(meal_name3), meal_name4 = VALUES(meal_name4), 
            meal_name5 = VALUES(meal_name5);
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    user_query,
                    [user_dump['user_name'], user_dump['energy_unit']] + user_dump['meal_names'] +
                    [None] * (6 - len(user_dump['meal_names']))
                )

                connection.commit()

    except mysql.connector.Error as error:
        print(error, file=sys.stderr)

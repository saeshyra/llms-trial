
import mysql.connector
import sys


#routine to ignore unauthorised users' messages
def verify_user(user):

    user_query = '''
        SELECT 
            telegram_user,mfp_user,sender_id
        FROM authorised_users WHERE telegram_user = %s;
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                cursor.execute(user_query, [user])
                row = cursor.fetchone()

    except Exception as e:
        print('ERROR DURING USER VERIFICATION:')
        print(e)
        row = ''
    return row if row else (None,None,None)

def get_all_users_from_db():

    user_query = '''
        SELECT DISTINCT telegram_user,mfp_user,first_name,sender_id,group_num,timezone
        FROM authorised_users;
    '''

    with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
        with connection.cursor() as cursor:
            cursor.execute(user_query)
            rows = cursor.fetchall()
    
    return rows if rows else None

#routine to ignore unauthorised users' messages
def get_user_from_db(telegram_user=None, sender_id=None):
    row = (None,None,None,None,None,None)

    try:
        if telegram_user:
            user_query = '''
                SELECT telegram_user,mfp_user,first_name,sender_id,group_num,timezone
                FROM authorised_users WHERE telegram_user = %s;
            '''
            with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
                with connection.cursor() as cursor:
                    cursor.execute(user_query, [telegram_user])
                    row = cursor.fetchone()
        
        if sender_id:
            user_query = '''
                SELECT telegram_user,mfp_user,first_name,sender_id,group_num,timezone
                FROM authorised_users WHERE sender_id = %s;
            '''
            with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
                with connection.cursor() as cursor:
                    cursor.execute(user_query, [sender_id])
                    row = cursor.fetchone()
 
    except Exception as e:
        print('ERROR DURING TOKEN EXTRACTION:')
        print(e)
        row = ''
    return row if row else (None,None,None,None,None,None)

def get_user_group_from_db(sender_id):
    user_query = '''
        SELECT group_num
        FROM authorised_users WHERE sender_id = %s;
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                cursor.execute(user_query, [sender_id])
                row = cursor.fetchone()
 
    except Exception as e:
        print('ERROR DURING TOKEN EXTRACTION:')
        print(e)
        row = ''
    return row[0] if row else None

def add_user_to_db(telegram_username, mfp_username, first_name, sender_id, group_num, timezone):
    user_query = '''
            INSERT INTO authorised_users (telegram_user, mfp_user, first_name, sender_id, group_num, timezone)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE telegram_user = VALUES(telegram_user),
                                    mfp_user = VALUES(mfp_user),
                                    first_name = VALUES(first_name),
                                    sender_id = VALUES(sender_id),
                                    group_num = VALUES(group_num),
                                    timezone = VALUES(timezone);
    '''
    #data = (client, expiration_date, username)
    data = (telegram_username, mfp_username, first_name, sender_id, group_num, timezone)
    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                cursor.execute(user_query,data)
                connection.commit()

    except mysql.connector.Error as error:
        print("ERROR in put_client")
        print(error, file=sys.stderr)

    user_query = '''
            INSERT INTO user (name, low_numeracy, consequences, report_day, report_hour, threshold, energy_report,
                              carbohydrate_report, fat_report, s_report, sugar_report, protein_report, sodium_report,
                              energy_unit, meal_name0, meal_name1, meal_name2, meal_name3, meal_name4, meal_name5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE name = VALUES(name), low_numeracy = VALUES(low_numeracy), consequences = VALUES(consequences),
                                    report_day = VALUES(report_day), report_hour = VALUES(report_hour),
                                    threshold = VALUES(threshold), energy_report = VALUES(energy_report),
                                    carbohydrate_report = VALUES(carbohydrate_report), fat_report = VALUES(fat_report),
                                    s_report = VALUES(s_report), sugar_report = VALUES(sugar_report),
                                    protein_report = VALUES(protein_report), sodium_report = VALUES(sodium_report),
                                    energy_unit = VALUES(energy_unit), meal_name0 = VALUES(meal_name0),
                                    meal_name1 = VALUES(meal_name1), meal_name2 = VALUES(meal_name2),
                                    meal_name3 = VALUES(meal_name3), meal_name4 = VALUES(meal_name4),
                                    meal_name5 = VALUES(meal_name5);
    '''
    data = (mfp_username, True, True, 0, 0, 10,
            True, True, True, True, True, True, True,
            'calories', '', '', '', '', '', '')
    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                cursor.execute(user_query,data)
                connection.commit()

    except mysql.connector.Error as error:
        print("ERROR in add_user_to_db")
        print(error, file=sys.stderr)


def get_user_prefs(user):
    dump = {}

    user_query = '''
        SELECT 
            low_numeracy, consequences, report_day, report_hour, threshold, energy_report, fat_report, 
            carbohydrate_report, sugar_report, protein_report, sodium_report 
        FROM user WHERE name = %s;
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                keys = ['energy', 'fat', 'carbohydrates', 'sugar', 'protein', 'sodium']
                cursor.execute(user_query, [user])
                user_row = cursor.fetchone()

                dump = {
                    'user_name': user,
                    'low_numeracy': bool(user_row[0]),
                    'consequences': bool(user_row[1]),
                    'report_day': user_row[2],
                    'report_hour': user_row[3],
                    'threshold': user_row[4],
                    'keys': [keys[key_id] for key_id, report in enumerate(user_row[5:]) if report],
                }
    except Exception as e:
        print('ERROR AT PREFERENCE MANAGEMENT LEVEL:')
        print(e)
        dump = {
            'user_name': user,
            'low_numeracy': False,
            'consequences': True,
            'report_day': None,  # TODO: handle
            'report_hour': None,  # TODO: handle
            'threshold': 10,
            'keys': ['energy', 'fat', 'carbohydrates', 'sugar', 'protein', 'sodium'],
        }

    return dump


def update_user_prefs(dump):
    user_query = '''
        UPDATE user 
        SET 
            low_numeracy = %s, consequences = %s, report_day = %s, report_hour = %s, threshold = %s, energy_report = %s, 
            fat_report = %s, carbohydrate_report = %s, sugar_report = %s, protein_report = %s, sodium_report = %s
        WHERE name = %s;
    '''

    try:
        with mysql.connector.connect(host='localhost', db='philhumans', user='root', password='root') as connection:
            with connection.cursor() as cursor:
                keys = ['energy', 'fat', 'carbohydrates', 'sugar', 'protein', 'sodium']
                cursor.execute(
                    user_query,
                    [
                        dump['low_numeracy'], dump['consequences'], dump['report_day'], dump['report_hour'],
                        dump['threshold']
                    ] + [key in dump['keys'] for key in keys] + [dump['user_name']]
                )

                connection.commit()

    except mysql.connector.Error as error:
        print("ERROR in loads")
        print(error, file=sys.stderr)

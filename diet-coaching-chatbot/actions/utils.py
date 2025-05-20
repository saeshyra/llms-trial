import json
import requests
import pandas as pd, \
    calendar
from rasa_sdk.events import *
from fuzzywuzzy import fuzz
from communication_layer.communicator import Communicator
from communication_layer.text_formatter import TextFormatterUtility
from dateutil import relativedelta, parser
from pytz import timezone

import torch
from peft import AutoPeftModelForCausalLM
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, BitsAndBytesConfig

# url = 'http://localhost:11434/api/generate'
# payload_json = json.dumps({"model": "llama3", "keep_alive": -1})
# headers = {'Content-Type': 'application/json'}
# response = requests.post(url, data=payload_json.encode('utf-8'), headers=headers)

# # Check if the request was successful (status code 200)
# if response.status_code == 200:
#     print('llama3 loaded into memory')
# else:
#     print("ERROR LOADING LLAMA3 INTO MEMORY:", response.status_code, 'response:', response.content.decode('utf-8'))

communicator = Communicator()
text_formatter = TextFormatterUtility()

more_info_mappings = {
    'Average intake and toughest day': [0, 1],
    'Intake trend and consistency': [2, 3],
    'Food analysis': [4, 5]
}

adv_insight_mappings = {
    ('intake', 'toughest', 'day'): [0, 1],
    ('trend', 'consistency'): [2, 3],
    ('food', ''): [4, 5]
}

nutrients_lookup = ['energy', 'calories', 'carbohydrates', 'protein', 'fat', 'sodium', 'sugar']#, 'preferences']
adv_insights_lookup = ['food', 'trend', 'intake', 'day', 'toughest day', 'toughest', 'consistency']

timezones = {
    'EDT': timezone('America/New_York'),
    'CEST': timezone('Europe/Berlin'),
    'IST': timezone('Asia/Kolkata'),
    'AEST': timezone('Australia/Sydney')
}

finetuned_model_dir = f"Meta-Llama-3-8B_finetuned_hai-coaching_new"

# BitsAndBytesConfig int-4 config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    # bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

# Load finetuned LLM model and tokenizer
counselling_model = AutoPeftModelForCausalLM.from_pretrained(
    finetuned_model_dir,
    quantization_config=bnb_config,
    device_map="auto",
)
counselling_tokenizer = AutoTokenizer.from_pretrained(finetuned_model_dir)
TASK_PREFIXES = {'reflection': 'Below is a diet struggle. Provide a reflection to understand what they mean.',
                 'comfort':    'Below is a diet struggle. Provide comfort to explain how it is normal to experience.',
                 'reframing':  'Below is a diet struggle. Provide some reframing to tell them how to see it in a more positive way.',
                 'suggestion': 'Below is a diet struggle. Provide a suggestion on how they can face the struggle.'}

def sort_nutrients(slots):
    if slots == 'preferences':
        return slots
    return [ordered for ordered in nutrients_lookup if ordered in slots]

def message_debug_print(messages):
    for message in messages:
        if type(message) == list:
            for el in message:
                print(f'{str(el)[:100]}...')
            print('//////////////////////////////')
        else:
            print(f'{str(message)[:100]}...')
    print('------------------------')

def slot_typo_handler(slots, known_values):
    if slots in [None,'None',[], False]:
        return []
    else:
        if type(slots) != list:
            slots = [slots]
        corrected_slots = []
        for slot in slots:
            distances = [(known, fuzz.ratio(slot.lower(), known.lower())) for known in known_values]
            distances.sort(key=lambda x: x[1], reverse=True)
            top_candidate = distances[0][0]
            if top_candidate == 'calories':
                top_candidate = 'energy'  # TODO: horrible, but RASA 3.0 seems to have introduced metadata access in NLU, so synonyms could be handled in custom pipeline component
            corrected_slots.append(top_candidate)
        return set(corrected_slots)

def date_validation(date_str):
    try:
        datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
        return True
    except ValueError:
        return False

def slot_reset():
    return [SlotSet('nutrient', []), SlotSet('time', []), SlotSet('nutrient', []), SlotSet('adv_insight', False)]

def extract_periods(entities, target_n, tz=None):
    print('extracting dates')
    today = datetime.date.today()
    dates = []
    
    duckling_entities = list(filter(lambda x: (x['entity'] == 'time' and x['extractor'] == 'DucklingEntityExtractor'), entities))
    other_entities = list(filter(lambda x: (x['entity'] == 'time' and x['extractor'] != 'DucklingEntityExtractor'), entities))

    if len(entities) > target_n \
            or len(entities) == target_n and duckling_entities and other_entities and duckling_entities[0]['text'] == other_entities[0]['value']:
        entities = duckling_entities
        
    if target_n == 2 and len(duckling_entities) == 1 and \
            'may' not in [duckling_entity['text'].lower() for duckling_entity in duckling_entities]:
        for other_entity in other_entities:
            if 'may' in other_entity['value'].lower():
                entities = duckling_entities + [other_entity]
        
    # handle month ranges with may
    for other_entity in other_entities:
        if 'to may' in other_entity['value'].lower():
            for duckling_entity in duckling_entities:
                if other_entity['value'].lower() not in duckling_entity['text'].lower() and \
                        len(other_entity['value'].lower().split()) > 2 and \
                        other_entity['value'].lower().split()[other_entity['value'].lower().split().index('to')-1] in duckling_entity['text'].lower():
                    try:
                        new_entity = {'start': other_entity['start'],
                                      'end': other_entity['end'],
                                      'text': other_entity['value'],
                                      'value': {'to': '2025-06-01T00:00:00.000+02:00',
                                                'from': duckling_entity['value']},
                                      'confidence': 1.0,
                                      'additional_info': {'values': [
                                          {'to': {'value': '2025-06-01T00:00:00.000+02:00', 'grain': 'month'},
                                           'from': {'value': duckling_entity['value'], 'grain': 'month'},
                                           'type': 'interval'}],
                                      'to': {'value': '2025-06-01T00:00:00.000+02:00', 'grain': 'month'},
                                      'from': {'value': duckling_entity['value'], 'grain': 'month'},
                                      'type': 'interval'},
                                      'entity': 'time',
                                      'extractor': 'DucklingEntityExtractor'}
                        duckling_entities[duckling_entities.index(duckling_entity)] = new_entity
                    except Exception as e:
                        print(f"failed to parse date range {other_entity['value']}: {e}")
                        continue
        elif 'may to' in other_entity['value'].lower():
            for duckling_entity in duckling_entities:
                if other_entity['value'].lower() not in duckling_entity['text'].lower() and \
                        len(other_entity['value'].lower().split()) > 2 and \
                        other_entity['value'].lower().split()[other_entity['value'].lower().split().index('to')+1] in duckling_entity['text'].lower():
                    try:
                        original_date = parser.parse(duckling_entity['value'])
                        new_date = original_date + relativedelta.relativedelta(months=+1)
                        new_entity = {'start': other_entity['start'],
                                      'end': other_entity['end'],
                                      'text': other_entity['value'],
                                      'value': {'to': new_date.isoformat(),
                                                'from': '2025-05-01T00:00:00.000+02:00'},
                                      'confidence': 1.0,
                                      'additional_info': {'values': [
                                          {'to': {'value': new_date.isoformat(), 'grain': 'month'},
                                           'from': {'value': '2025-05-01T00:00:00.000+02:00', 'grain': 'month'},
                                           'type': 'interval'}],
                                      'to': {'value': new_date.isoformat(), 'grain': 'month'},
                                      'from': {'value': '2025-05-01T00:00:00.000+02:00', 'grain': 'month'},
                                      'type': 'interval'},
                                      'entity': 'time',
                                      'extractor': 'DucklingEntityExtractor'}
                        duckling_entities[duckling_entities.index(duckling_entity)] = new_entity
                    except Exception as e:
                        print(f"failed to parse date range {other_entity['value']}: {e}")
                        continue

    for entity in entities:#tracker.latest_message['entities']:
        if 'additional_info' in entity:
            if 'from' in entity['additional_info']:
                if 'to' in entity['additional_info'] and entity['additional_info']['to']:

                    start_date = entity['additional_info']['from']['value'][:10]
                    if 'today' in entity['text'] or 'yesterday' in entity['text'] or 'tomorrow' in entity['text']:
                        start_date = convert_timezone(start_date, tz)
                    start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                    if start.year > today.year:
                        start = datetime.date(start.year - 1, start.month, start.day)

                    end_date = entity['additional_info']['to']['value'][:10]
                    if 'today' in entity['text'] or 'yesterday' in entity['text'] or 'tomorrow' in entity['text']:
                        end_date = convert_timezone(end_date, tz)
                    end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date() - datetime.timedelta(1)
                    if end.year > today.year:
                        end = datetime.date(end.year - 1, end.month, end.day)

                    interval = pd.date_range(start=start, end=end).to_pydatetime().tolist()
                    dates.append([d.date() for d in interval])  # .date to keep same type of data

                else:
                    grain = entity['additional_info']['from']['grain']

                    date = entity['additional_info']['from']['value'][:10]
                    if 'today' in entity['text'] or 'yesterday' in entity['text'] or 'tomorrow' in entity['text']:
                        date = convert_timezone(date, tz)
                    day = datetime.datetime.strptime(date, '%Y-%m-%d').date()

                    if day.year > today.year:
                        day = datetime.date(day.year - 1, day.month, day.day)
                    interval = None
                    if grain == 'week':
                        interval = list(range(min((today - day).days + 1, 7)))
                    elif grain == 'month':
                        interval = list(range(min((today - day).days + 1, calendar.monthrange(day.year, day.month)[1])))
                    elif grain == 'year':
                        interval = list(
                            range(min((today - day).days + 1, (datetime.date(day.year + 1, 1, 1) - day).days)))
                    days = [day + datetime.timedelta(d) for d in interval] if interval else [day]
                    dates.append(days)

            elif 'grain' in entity['additional_info']:
                grain = entity['additional_info']['grain']

                date = entity['value'][:10]
                if 'today' in entity['text'] or 'yesterday' in entity['text'] or 'tomorrow' in entity['text']:
                    date = convert_timezone(date, tz)
                day = datetime.datetime.strptime(date, '%Y-%m-%d').date()

                if day.year > today.year:
                    day = datetime.date(day.year - 1, day.month, day.day)
                if grain == 'day':
                    interval = None
                elif grain == 'week':
                    interval = list(range(min((today - day).days + 1, 7)))
                elif grain == 'month':
                    interval = list(range(min((today - day).days + 1, calendar.monthrange(day.year, day.month)[1])))
                elif grain == 'year':
                    interval = list(range(min((today - day).days + 1, (datetime.date(day.year + 1, 1, 1) - day).days)))
                else:
                    interval = []
                days = [day + datetime.timedelta(d) for d in interval] if interval else [day]
                dates.append(days)

            else:
                if 'from' in entity['value']:
                    start_date = entity['value']['from'][:10]
                else:
                    start_date = entity['value'][:10]
                    
                if 'today' in entity['text'] or 'yesterday' in entity['text'] or 'tomorrow' in entity['text']:
                    start_date = convert_timezone(start_date, tz)
                start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()

                if 'to' in entity['value']:
                    end_date = entity['value']['to'][:10]
                else:
                    end_date = entity['value'][:10]
            
                if 'today' in entity['text'] or 'yesterday' in entity['text'] or 'tomorrow' in entity['text']:
                    end_date = convert_timezone(end_date, tz)
                end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                
                days = [start + datetime.timedelta(d) for d in range((end - start).days)]
                dates.append(days)

        elif entity['extractor'] == 'DIETClassifier' and 'may' in entity['value'].lower() and len(entity['value'].lower().split()) < 3:
            day = datetime.datetime.strptime('05/2024', '%m/%Y').date()
            interval = list(range(min((today - day).days + 1, calendar.monthrange(day.year, day.month)[1])))
            days = [day + datetime.timedelta(d) for d in interval] if interval else [day]
            dates.append(days)
            
            # [{'start': 6, 'end': 11, 'text': 'april', 'value': '2025-04-01T00:00:00.000-07:00', 'confidence': 1.0,
            #   'additional_info': {
            #       'values': [{'value': '2025-04-01T00:00:00.000-07:00', 'grain': 'month', 'type': 'value'},
            #                  {'value': '2026-04-01T00:00:00.000-07:00', 'grain': 'month', 'type': 'value'},
            #                  {'value': '2027-04-01T00:00:00.000-07:00', 'grain': 'month', 'type': 'value'}],
            #       'value': '2025-04-01T00:00:00.000-07:00', 'grain': 'month', 'type': 'value'},
            #       'entity': 'time', 'extractor': 'DucklingEntityExtractor'}]
            
            # [{'entity': 'time', 'start': 6, 'end': 9, 'confidence_entity': 0.9231367111206055, 'value': 'may', 'extractor': 'DIETClassifier'}]
        
    if len(dates) == target_n:
        return dates  # we don't need lists of lists in update, TODO: fix in future
    
    return None

def extract_last_action(tracker):
    reversed_tracker = list(reversed(tracker.events))
    last_intent_struct = None
    last_action = None
    if len(tracker.events) >= 300:
        reversed_tracker = reversed_tracker[:300]
    for event in reversed_tracker:
        if event['event'] == 'user':
            found_intent = False
            entity_keys = []
            for entity in event['parse_data']['entities']:
                for key in entity.keys():
                    entity_keys.append(key)
            if len(event['parse_data']['entities']) > 0 and len(
                    [x for x in entity_keys if x in ['time', 'additional_info']]) > 0:
                for entity in event['parse_data']['entities']:
                    if 'additional_info' in entity:
                        last_intent_struct = event['parse_data']
                        last_action = last_intent_struct["intent"]["name"]
                        last_action = f'{"action_" if "action_" not in last_action else ""}{last_action.strip(".py")}'
                        if last_action != 'action_more_info':
                            found_intent = True
                            break
                if found_intent:
                    return last_action, last_intent_struct
                else:
                    print('UNABLE TO RETRIEVE LAST INTENT AND ACTION')
                    return 'action_update', {}
    return last_action, last_intent_struct

def get_imputation_button():
    buttons = [
        {"payload": "/confirm_button", "title": "Yes"},
        {"payload": "/empty_message_stack_on_button", "title": "No "},
    ]
    text = list(communicator.realise(intent='holes_inside_warn'))[0][0]['content']
    message = ({'type': 'button',
                'content': {
                    'text': text,
                    'buttons': buttons,
                    'button_type': 'vertical'
                }}, {})
    return [message]

def get_more_info_button(nutrient=None):
    if nutrient:
        text = f'Would you like me to go on with your {nutrient.upper()} intake?'
    else:
        text = 'Would you like me to continue?'
    buttons = [
        {"payload": "/confirm_button", "title": "Yes"},
        {"payload": "/empty_message_stack_on_button", "title": "No "},
    ]
    message = {'type': 'button',
               'content': {
                   'text': text,
                   'buttons': buttons,
                   'button_type': 'vertical'}
               }

    return [message]

def get_content_filter_button(slot, more_info_filter):
    options = []
    for title, indexes in more_info_mappings.items():
        button_index = [str(k) for k in more_info_mappings.keys()].index(title)
        button_str = str(button_index)
        options.append({"payload": '/filter_chosen{"more_info_filter": "' + button_str + '"}',
                        "title": title + '   ' + (text_formatter.get_emoji(
                            'green_circle') if button_index in more_info_filter else text_formatter.get_emoji(
                            'empty_circle'))})
    if more_info_filter:
        options.append(
            {"payload": '/confirmed_filters', "title": 'Confirm and submit ' + text_formatter.get_emoji('good_news')})
    options.append(
        {"payload": "/empty_message_stack_on_button", "title": 'Cancel ' + text_formatter.get_emoji('cancel_button')})
    text = [(clean_message, struct_message) for clean_message, struct_message in
                          communicator.realise(intent='filter_more_info_button', data=slot)][0][0]['content']
    message = {'type': 'button',
               'content': {'text': text,
                           'buttons': options,
                           'button_type': 'vertical'}}
    return [message]

def get_counselling_buttons():
    text = 'Would you like some help with a struggle?'
    buttons = [
        {"payload": "/affirm_counselling", "title": "Yes please " + text_formatter.get_emoji('persevere')},
        {"payload": "/deny_counselling", "title": "Nope, I'm doing great " + text_formatter.get_emoji('polite_smile')},
    ]
    message = {'type': 'button',
               'content': {
                   'text': text,
                   'buttons': buttons,
                   'button_type': 'vertical'}
               }

    return [message]

def get_retry_counselling_buttons():
    text = 'Hmm... Would you like to try explaining again? It can help to give some extra sentences to describe your problem!'
    buttons = [
        {"payload": "/affirm_counselling", "title": "Sure, I'll rephrase " + text_formatter.get_emoji('confused')},
        {"payload": "/deny_counselling", "title": "No, that's okay " + text_formatter.get_emoji('sad')},
    ]
    message = {'type': 'button',
               'content': {
                   'text': text,
                   'buttons': buttons,
                   'button_type': 'vertical'}
               }

    return [message]

def get_feedback_buttons():
    text = 'Was this helpful?'
    buttons = [
        {"payload": "/positive_feedback", "title": "Yes"},
        {"payload": "/negative_feedback", "title": "No"},
    ]
    message = {'type': 'button',
               'content': {
                   'text': text,
                   'buttons': buttons,
                   'button_type': 'vertical'}
               }

    return [message]

def get_check_diary_buttons():
    buttons = [
        {"payload": "/all_fixed", "title": "Sorry, I've fixed it now! " + text_formatter.get_emoji('happy')},
        {"payload": "/already_correct", "title": "Actually, everything looks correct " + text_formatter.get_emoji('good_news')},
    ]
    message = {'type': 'button',
               'content': {
                   'buttons': buttons,
                   'button_type': 'vertical'}
               }

    return [message]

def incorporate_charts(charts, messages):
    messages = list(map(lambda m: list(filter(lambda c: c['content']['chart_name'] == m[0]['content'],
                                              charts))[0] if m[0]['type'] == 'text' and 'CHART' in m[0][
        'content'] else m,
                        messages))
    return messages

def format_instruction(struggle, text_type):
    return f"""
{TASK_PREFIXES[text_type]}

### Struggle:
{struggle}

### {text_type.upper()+text_type[1:]}:
"""

def generate_counselling_response(struggle, text_type):
    with torch.inference_mode():
        input_ids = counselling_tokenizer(format_instruction(struggle, text_type), return_tensors="pt", truncation=True).input_ids.cuda()
        outputs = counselling_model.generate(
            input_ids,
            pad_token_id=counselling_tokenizer.eos_token_id,
            max_new_tokens=256,
            do_sample=True,
            top_p=0.9,
            temperature=0.6,
        )
        output_ids = outputs[0]
        prediction = counselling_tokenizer.decode(output_ids, skip_special_tokens=True)[len(format_instruction(struggle, text_type)):]
        return prediction.strip()

def rephrase(message, intent, nutrient=False):
    print('\n***********MESSAGE************\n' + message + '\n******************************')

    general_prompt = 'Do not include additional information. Use simple language and emojis. Rephrase the following message to the user.'
    contexts = {
        'check_diary': "You are checking if the user made an error while filling in their food diary yesterday. Tell the user exactly what you noticed. ",
        'compare': 'The user requested comparative insights into their {} intake between two specified periods. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ',
        'compare_average': "The user requested comparative insights into their average {} intake and toughest day between two specified periods. Specified periods must be longer than one day to calculate toughest day. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ",
        'compare_trend': 'The user requested comparative insights into the trends and consistency of their {} intake between two specified periods. This can only be calculated if they specify periods both longer than 3 days. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ',
        'compare_food': 'The user requested comparative insights into the food items that contributed to their {} intake between two specified periods. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ',
        'compare_no_dates': 'The user requested comparative insights into their food diary but did not give dates. Do not greet the user. ',
        'compare_one_date': 'The user requested comparative insights into their food diary but only gave one date. Do not greet the user. ',
        'compare_many_dates': 'The user requested comparative insights into their food diary but gave too many dates. Do not greet the user. ',
        'counselling': 'The user requested help with a diet struggle. ',
        'retry_counselling': "The user requested help with their diet, but you didn't understand their issue. ",
        'empty': "The user requested insights into their food diary for a time period with no data. ",
        'empty_message_stack': 'The user has chosen to end the flow of information and buttons. ',
        'filter_more_info_button': 'The user is offered button options below for different types of advanced insights of their food diary. Keep the heading. Do not assume the options. ',
        'holes_inside_warn': "The user's food diary has empty days in the specified period, so insights will be calculated without the empty days. Mention any removed dates but do not assume the time period. ",
        'holes_surrounding_warn': "The user's food diary has empty days in the specified period, so insights will be calculated without the empty days. Mention any removed dates but do not assume the time period. Do not ask questions. ",
        'invalid_button': 'The user has clicked on a previous button for more advanced insights that is now outdated. You cannot retrieve this information. Do not apologise. ',
        'more_info_denied': "The user's food diary has estimated days that were empty in the specified period, so insights cannot be calculated. ",
        'most_data_missing': "The user's food diary has too many empty days in the specified period, so insights cannot be calculated. Do not ask questions. ",
        'no_dates': 'The user requested insights of their food diary but did not specify dates in the correct format. Do not include greetings. ',
        'no_dates_default': 'The user requested insights into their food diary but did not specify dates in the correct format. Do not include greetings. ',
        'no_more': 'The user requested more information after all the information was given. ',
        'no_multiple_times': 'The user either mentioned more than one time period for insights into their food diary, or more than two time periods for a comparison. Use the same examples. ',
        # 'partial_typo': '',
        'query_complexity_excess': 'The user requested insights into their food diary over a specified period longer than the maximum of 5 months. ',
        'update': 'The user requested insights into their {} intake over a specified period. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ',
        'update_average': "The user requested insights into their average {} intake and toughest day over a specified period. The specified period must be longer than one day to calculate toughest day. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ",
        'update_trend': 'The user requested insights into the trends and consistency of their {} intake over a specified period. This can only be calculated if they specify a period longer than 3 days. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ',
        'update_food': 'The user requested insights into the food items that contributed to their {} intake over a specified period. Keep all information including all percentages of daily goal. Do not greet the user or prompt a response. ',
        'wait': 'The user requested insights into their food diary for the specified period. Keep all mentioned dates. ',
        'wait_more': 'The user requested advanced insights into their food diary. ',
        'weird_comparison': 'The user requested comparative insights into their food diary across two time periods that overlap, are non-consecutive or are different in length. Do not ask questions. ',
    }
    if intent in ['update', 'compare'] and nutrient:
        if 'AVERAGE' in message:
            intent += '_average'
        elif 'TREND' in message:
            intent += '_trend'
        elif 'FOOD' in message:
            intent += '_food'
            
        if not nutrient:
            nutrient = 'food'
        prompt = contexts[intent].format(nutrient) + general_prompt
        
    elif intent in contexts:
        prompt = contexts[intent] + general_prompt
    else:
        prompt = general_prompt

    url = 'http://localhost:11434/api/generate'
    payload = {
        "model": "llama3",
        "system": prompt
,
        "prompt": 'Rephrase the message:\n' + message,
        "options": {
            "temperature": 0.6
        },
        "keep_alive": -1,
        "stream": False
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    headers = {'Content-Type': 'application/json'}

    for _ in range(3):
        response = requests.post(url, data=payload_json.encode('utf-8'), headers=headers)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            output = json.loads(response.content.decode('utf-8'))['response']

            if '[' in output or '(' in output:
                continue # retry rephrasing

            # use message after first colon if message starts with something like "Here's a rephrased version of the message:"
            if 'rephrase' in output or 'Rephrase' in output:
                if ':' in output:
                    print('removing introduction')
                    colon_pos = output.index(':')
                    output = output[colon_pos+1:]
                else: # retry rephrasing
                    continue

            print('\n**********REPHRASED***********\n' + output.strip() + '\n******************************')
            # use message in quotes if quotes present
            output = output.strip()
            if '"' in output[:5]:
                start_quote_pos = output.index('"')
                if '"' in output[start_quote_pos+1:]:
                    print('removing quotations')
                    end_quote_pos = output[start_quote_pos+1:].index('"')
                    output = output[start_quote_pos+1:start_quote_pos+end_quote_pos]
            
            # lazy attempt at keeping spelling consistent
            output = output.replace('analyz', 'analys').replace('Analyz', 'Analys').replace('stabiliz', 'stabilis').replace('Stabiliz', 'Stabilis')

            return output
        
        else:
            print("ERROR IN REPHRASING REQUEST:", response.status_code, 'response:', response.content.decode('utf-8'))
            return message
    
    # rephrasing kept returning bad results
    return message

def convert_timezone(date, timezone):
    if timezone == 'CEST' or timezone is None:
        return date
    
    try:
        # original_datetime = datetime.datetime.fromisoformat(time)
        original_date = parser.parse(date)
        default_timezone = timezones['CEST']
        target_timezone = timezones[timezone]

        # Get current time with the same timezone
        current_time = datetime.datetime.now(default_timezone)
        original_datetime = original_date.replace(hour=current_time.hour, minute=current_time.minute, second=current_time.second)

        target_time = original_datetime.astimezone(target_timezone)
        print('new time:', target_time.isoformat())
        return target_time.isoformat()[:10]
    except Exception as e:
        print(f'error converting timezone: {e}')
        return date
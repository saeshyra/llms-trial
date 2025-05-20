from rasa_sdk.executor import CollectingDispatcher
import user_profiling_layer as upl, \
    data_handling_layer as dhl, \
    inspect, \
    itertools, \
    telebot, \
    copy, \
    sys, \
    json
import os
from time import sleep
from pydoc import locate
from rasa_sdk import *
from .utils import *
import json
import csv
from collections import defaultdict

import torch
from peft import AutoPeftModelForCausalLM
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, BitsAndBytesConfig

TRIAL_START_DATE = datetime.date(2024, 5, 13)

# global variables that let the chatbot inject special information for inter-action internal communication
# used to let users decide which part of more info they're interested in
more_info_filter = set()

# acts as a stack that incorporates the messages to send to user. Makes it possible to wait between the different "utter_messages" by calling "action_delivery_message" multiple times
message_stack = defaultdict(list)

#
current_batch = defaultdict(list)

# dinamically calculated based on each message length to give user the time to read
wait_time = 0

# used by split_long_content to remember which action should be re-called
target_class = None

#
more_info_exhausted = False

#
deliver_flow = defaultdict(list)

#
block_delivery = False

# refers to the last performed action, used during the "more_info" flow to communicate with buttons
last_action = None

#since user recognition routine must be ran for every intent, sometimes it duplicates (e.g.: wait + update)
unknown_user_notified = False


#TODO: warn about this file and those removed by gitignore in repo
with open('bot_credentials.json', 'r') as f:
  telegram_api_creds = json.load(f)

#auxiliary bot instance,used to delete messages
TOKEN = telegram_api_creds['token']
aux_bot = telebot.TeleBot(TOKEN)

communicator = Communicator()
text_formatter = TextFormatterUtility()

DEVICE = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

# nutritional counselling model
# counselling_model = AutoModelForSeq2SeqLM.from_pretrained('flan-t5-base_finetuned_hai-coaching')
# counselling_model.to(DEVICE)
# counselling_tokenizer = AutoTokenizer.from_pretrained('google/flan-t5-base')
# TASK_PREFIXES = {'reflection': 'provide a reflection to understand what they mean: ',
#                  'comfort':    'provide comfort to explain how it is normal to experience it: ',
#                  'reframing':  'provide some reframing to tell them how to see it in a more positive way: ',
#                  'suggestion': 'provide a suggestion on how they can face the struggle: '}

counselling_texts = {}


# class ActionNewUser(Action):
#     def name(self) -> Text:
#         return "action_new_user"

#     def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict]:
#         # Custom logic to process user and alias data
#         text = tracker.latest_message['text'].split(' ')
#         mfp_user = text[2]
#         telegram_user = text[3]

#         upl.preferences_management_module.add_user_to_db(mfp_user, telegram_user, None, tracker.sender_id, 1, 'CEST')
#         dispatcher.utter_message(text=f"mfp_user: {mfp_user}, telegram_user: {telegram_user}")

#         return []

class ActionRegisterUser(Action):
    def name(self) -> Text:
        return "action_register_user"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        if 'message' not in tracker.latest_message['metadata']:
            return []
        if 'message' in tracker.latest_message['metadata'] and \
                'chat' in tracker.latest_message['metadata']['message'] and \
                'username' in tracker.latest_message['metadata']['message']['chat']:
            user_approaching = tracker.latest_message['metadata']['message']['chat']['username']
        else:
            user_approaching = None
        telegram_user, mfp_user, first_name, sender_id, group_num, timezone = upl.preferences_management_module.get_user_from_db(telegram_user=user_approaching)
        
        if user_approaching and telegram_user and user_approaching.lower() == telegram_user.lower() and not sender_id:
            upl.preferences_management_module.add_user_to_db(telegram_user, mfp_user, first_name, tracker.sender_id, group_num, timezone)

        if first_name and group_num:
            return [SlotSet('name', first_name)]
        return []

#TODO: impossible as for now since the message id can't be tracked until the user interact with the buttons at least one time
class ActionDeleteLeftoverButtons(Action):
    def name(self) -> Text:
        return 'action_delete_leftover_buttons'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global message_stack

        api_id = telegram_api_creds['apid_id']
        api_hash = telegram_api_creds['api_hash']

        reversed_tracker = list(reversed(tracker.applied_events()))[:30]

        #for event in reversed_tracker:
        #    pprint.pprint(event)
        #    print('/////////////////////////////////')
        #    if ('metadata' in event and 'callback_query' in event['metadata']) and ('reply_markup' in event['metadata']['callback_query']['message']):
        #        chat_id = event['metadata']['callback_query']['message']['chat']['id']
        #        message_id = event['metadata']['callback_query']['message']['message_id']
        #        ActionDeleteButton.delete_arbitrary(self, chat_id, message_id)

class ActionVerifyAccess(Action):
    def name(self) -> Text:
        return 'action_verify_access'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # if datetime.date.today() < TRIAL_START_DATE and tracker.get_intent_of_latest_message() != 'trial_start':
        #     dispatcher.utter_message("You can start logging your meals, but I won't be able to chat before the trial starts on May 13th. Wait for my friend request on MyFitnessPal, and come back after you've accepted!")
        #     return [ConversationPaused()]
        # if not self.verify(dispatcher, tracker):
        #     return [Restarted()]
        return []

    def verify(self, dispatcher, tracker):
        global message_stack, unknown_user_notified
        if 'message' not in tracker.latest_message['metadata'] or \
                'chat' not in tracker.latest_message['metadata']['message'] or \
                'username' not in tracker.latest_message['metadata']['message']['chat']:
            return False
        user_approaching = tracker.latest_message['metadata']['message']['chat']['username']
        # telegram_user, mfp_user, sender_id = upl.preferences_management_module.verify_user(user_approaching)
        telegram_user, mfp_user, first_name, sender_id, group_num, timezone = upl.preferences_management_module.get_user_from_db(telegram_user=user_approaching)
        
        if telegram_user and user_approaching.lower() != telegram_user.lower() or group_num is None:
            action_deliver = ActionDeliverMessage()  # TODO substitute with classic ActionTriggerDeliver call
            if not unknown_user_notified:
                for clean_message, struct_message in communicator.realise(data={}, intent='unauthorised_user'):
                    action_deliver.process_message((clean_message, struct_message, 'unauthorised_user'), tracker, dispatcher)
                unknown_user_notified = True
            else:
                unknown_user_notified = False
            return False
        
        if sender_id is None: # add sender_id to database
            # _, _, first_name, _, group_num, timezone = upl.preferences_management_module.get_user_from_db(telegram_user=telegram_user)
            upl.preferences_management_module.add_user_to_db(telegram_user, mfp_user, first_name, tracker.sender_id, group_num, timezone)
            if first_name and group_num is not None:
                tracker.slots['name'] = first_name

        return mfp_user

class ActionCheckCounselling(Action):
    def name(self) -> Text:
        return "action_check_counselling"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # if 'message' in tracker.latest_message['metadata']:
        #     username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        user_group = upl.preferences_management_module.get_user_group_from_db(tracker.sender_id)
        return [SlotSet("counselling", (user_group is not None and user_group==3))]

class ActionCheckRephrasing(Action):
    def name(self) -> Text:
        return "action_check_rephrasing"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # if 'message' in tracker.latest_message['metadata']:
        #     username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        user_group = upl.preferences_management_module.get_user_group_from_db(tracker.sender_id)
        print('user group:', user_group)
        return [SlotSet("rephrasing", (user_group is not None and user_group!=1))]

class ActionUpdate(Action):
    def name(self) -> Text:
        return 'action_update'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global message_stack, username, password

        print('\n**********UPDATE**********')
        print('update tracker slots:', tracker.slots)

        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0
        _, _, _, _, _, timezone = upl.preferences_management_module.get_user_from_db(telegram_user=username)

        batch = []
        adv_insight = list(slot_typo_handler(tracker.slots['adv_insight'], adv_insights_lookup))
        nutrients = list(slot_typo_handler(tracker.slots['nutrient'], nutrients_lookup)) if tracker.slots['nutrient'] not in [[],'preferences'] \
                                                                                         else upl.dumps(username)['keys']
        nutrients = sort_nutrients(nutrients)

        more_info = tracker.slots['more_info'] if 'more_info' in tracker.slots else False
        # if tracker.slots['time'] is not None:
        #     tracker.slots['time'] = [el for el in tracker.slots['time'] if isinstance(el, dict) or date_validation(el)]
        time_entities = list(filter(lambda x: (x['entity'] == 'time'), tracker.latest_message['entities']))
        print('update time entities:', time_entities)
        dates = extract_periods(time_entities, 1, timezone)

        if not dates or not dates[0]:
            dates = [[datetime.datetime.today().date()]]
            batch += [(clean_message, struct_message, 'no_dates') for clean_message, struct_message in
                        communicator.realise(intent='no_dates')]
            message_stack[tracker.sender_id].append(batch)
            return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
        elif len(dates) > 1:#isinstance(tracker.slots['time'], list) and len(tracker.slots['time']) > 1:
            batch += [(clean_message, struct_message, 'no_multiple_times') for clean_message, struct_message in
                      communicator.realise(intent='no_multiple_times')]
            message_stack[tracker.sender_id].append(batch)
            return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
        # else:
            # time_entities = list(filter(lambda x: (x['entity'] == 'time'), tracker.latest_message['entities']))
            # print('update time entities:', time_entities)
            # dates = extract_periods(time_entities, 1, timezone)
            # if not dates or not dates[0]:
            #     dates = [[datetime.datetime.today().date()]]
            #     batch += [(clean_message, struct_message, 'no_dates') for clean_message, struct_message in
            #               communicator.realise(intent='no_dates')]
            #     message_stack[tracker.sender_id].append(batch)
            #     return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
        elif len(dates[0]) > 150:  # TODO: this cases and others can be moved in DHL through a string return, and therefore handled in the below code
            batch += [(clean_message, struct_message, 'query_complexity_excess') for clean_message, struct_message in
                        communicator.realise(intent='query_complexity_excess')]
            message_stack[tracker.sender_id].append(batch)
            return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
            # else:
        print('dates:', dates[0])
        data = dhl.update(username, dates, nutrients)
        if data == 'mfp_error':
            return slot_reset() + [ActionExecuted("action_listen")] + \
                [UserUttered("/mfp_error", {"intent": {"name": "mfp_error", "confidence": 1.0}})]
        elif type(data) == str:
            ActionEmptyMessageStack.silent(self, tracker.sender_id)
            batch += [(clean_message, struct_message, data) for clean_message, struct_message in
                        communicator.realise(intent=data)]
            message_stack[tracker.sender_id].append(batch)
            return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
        else:
            refined_data = communicator.prepare_data(data, 'update')
            if len(refined_data['unk_keys']) > 0:
                unk = {'unk_keys': refined_data['unk_keys'], 'keys': refined_data['keys']}
                batch += [(clean_message, struct_message, 'partial_typo') for clean_message, struct_message in
                            communicator.realise(data=unk, intent='partial_typo')]
                if len(refined_data['unk_keys']) == len(refined_data['keys']) or refined_data['keys'] == []:
                    message_stack[tracker.sender_id].append(batch)
                    return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)

            if data['shrinked']:
                batch += [(clean_message, struct_message, 'holes_surrounding_warn') for clean_message, struct_message in
                            communicator.realise(data=data['shrinked'], intent='holes_surrounding_warn')]
                if not data['MI']:
                    message_stack[tracker.sender_id].append(batch)
            if data['MI']:
                if more_info:# or adv_insight:
                    print('more info denied')
                    return "more_info_denied"  # TODO: why not realising directly in here?
                elif adv_insight:
                    print('more info denied')
                    ActionEmptyMessageStack.silent(self, tracker.sender_id)
                    batch += [(clean_message, struct_message, 'more_info_denied') for clean_message, struct_message in
                            communicator.realise(intent='more_info_denied')]
                    message_stack[tracker.sender_id].append(batch)
                    return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
                else:  # TODO: split into two template -> one for asking confirmation and one for reminding after doing it
                    # UPDATE AFTER ESTIMATING DAYS
                    print('update after estimating days')
                    batch += [(clean_message, struct_message, None) for clean_message, struct_message in
                                communicator.realise(data=data, intent='update')]
                    message_stack[tracker.sender_id].append(get_imputation_button())
                    message_stack[tracker.sender_id].append(batch)
                    return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
            else:
                if more_info or adv_insight:
                    # MORE INFO WITH UPDATE
                    print('more info with update')
                    for nutrient in nutrients:
                        temp_data = data
                        temp_data['keys'] = [nutrient]
                        temp_refined_data = refined_data
                        temp_refined_data['keys'] = [nutrient]
                        percentages = [[perc for perc in [d['budget'][nutrient]['goal_percentage'] for d in data['days']]]]
                        charts = [{'type': 'chart',
                                    'content': {'chart_name': 'CHART_INTAKE',
                                                'chart_type': 'line',
                                                'args': {
                                                    'percentages': percentages,
                                                    'thresholds': temp_data['threshold'],
                                                    'data': refined_data,
                                                    'key': nutrient,
                                                    'quantify': False
                                                }}
                                    },
                                    {'type': 'chart',
                                    'content': {'chart_name': 'CHART_TREND',
                                                'chart_type': 'trend',
                                                'args': {
                                                    'percentages': percentages,
                                                    'thresholds': temp_data['threshold'],
                                                    'data': refined_data,
                                                    'key': nutrient,
                                                    'quantify': False
                                                }}
                                    },
                                    {'type': 'chart',
                                    'content': {'chart_name': 'CHART_FOOD',
                                                'chart_type': 'pie',
                                                'args': {
                                                    'foods_lists': [
                                                        temp_refined_data['diet'][nutrient]['foods']],
                                                    'key': nutrient,
                                                    'quantify': False
                                                }}
                                    }]
                        data['adv_insight'] = adv_insight
                        individual_batch = [(clean_message, struct_message, 'update', nutrient) for clean_message, struct_message in
                                            communicator.realise(data=temp_data, intent='update', more_info=True)]
                        individual_batch = incorporate_charts(charts, individual_batch)
                        if adv_insight:
                            # gets the mapping keys that produces a non-empty set together with the adv_insight specified by the user, then converts each one to the respective value (indexes)
                            indexes = list(map(lambda k: adv_insight_mappings[k],
                                                list(filter(
                                                    lambda k: len(set(adv_insight).intersection(set(k))) != 0,
                                                    adv_insight_mappings.keys())
                                                    )
                                                )
                                            )[0]
                            individual_batch = [individual_batch[i] for i in indexes]
                            if len(nutrients) > 1 and nutrient != nutrients[-1]:
                                individual_batch += get_more_info_button(nutrients[nutrients.index(nutrient)+1])
                        batch += individual_batch
                        if not adv_insight or adv_insight == []:
                            message_stack[tracker.sender_id].append(get_content_filter_button(nutrient, more_info_filter))
                        message_stack[tracker.sender_id].append(batch)
                        batch = []
                    return [] if not adv_insight else ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
            if not more_info:
                # REGULAR UPDATE
                print('regular update')
                batch += [(clean_message, struct_message, None) for clean_message, struct_message in
                            communicator.realise(data=data, intent='update')]
                message_stack[tracker.sender_id].append(batch)

        return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)

class ActionCompare(Action):
    def name(self) -> Text:
        return "action_compare"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0
        
        _, _, _, _, _, timezone = upl.preferences_management_module.get_user_from_db(telegram_user=username)
        
        print('\n**********COMPARE**********')
        print('compare tracker slots:', tracker.slots)

        global message_stack
        batch = []
        adv_insight = list(slot_typo_handler(tracker.slots['adv_insight'], adv_insights_lookup))
        nutrients = list(slot_typo_handler(tracker.slots['nutrient'], nutrients_lookup)) \
                        if tracker.slots['nutrient'] not in [[], 'preferences'] \
                        else upl.dumps(username)['keys']
        nutrients = sort_nutrients(nutrients)
        more_info = tracker.slots['more_info'] if 'more_info' in tracker.slots else False
        time_entities = list(filter(lambda x: (x['entity'] == 'time'), tracker.latest_message['entities']))
        print('compare entities:', time_entities)
        dates = extract_periods(time_entities, 2, timezone)
        # if tracker.slots['time'] is not None:
        #     tracker.slots['time'] = [el for el in tracker.slots['time'] if isinstance(el, dict) or date_validation(el)]
        if not dates or not dates[0]:#isinstance(tracker.slots['time'], list) or tracker.slots['time'] == 1:
            message = 'Please give me two dates or a date range to compare'
            if tracker.slots['rephrasing']:
                message = rephrase(message, intent='compare_no_dates')
            dispatcher.utter_message(text=message)
        elif len(dates) < 2:#len(tracker.slots['time']) < 2:
            message = '''It looks like you've only given me one date or date range! Could you give me two to compare?'''
            if tracker.slots['rephrasing']:
                message = rephrase(message, intent='compare_one_date')
            dispatcher.utter_message(text=message)
        elif len(dates) > 2:#len(tracker.slots['time']) > 2:
            message = '''I'm sorry, but I can only compare two dates or date ranges'''
            if tracker.slots['rephrasing']:
                message = rephrase(message, intent='compare_many_dates')
            dispatcher.utter_message(text=message)
        else:
            # time_entities = list(filter(lambda x: (x['entity'] == 'time'), tracker.latest_message['entities']))
            # print('compare entities:', time_entities)
            # dates = extract_periods(time_entities, 2, timezone)
            if not dates or len(dates) < 2:
                batch += [(clean_message, struct_message, 'no_dates') for clean_message, struct_message in
                          communicator.realise(intent='no_dates')]
                message_stack[tracker.sender_id].append(batch)
                return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
            elif len(dates) > 2:  # TODO: this cases and others can be moved in DHL through a string return, and therefore handled in the below code
                batch += [(clean_message, struct_message, 'query_complexity_excess') for clean_message, struct_message in
                          communicator.realise(intent='query_complexity_excess')]
                message_stack[tracker.sender_id].append(batch)
                return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
            else:
                if dates[0][0] < dates[1][0]:
                    less_recent = dates[0]
                    more_recent = dates[1]
                else:
                    more_recent = dates[0]
                    less_recent = dates[1]

                # handling potentially dangerous comparisons: periods that overlap, with different lengths or too distant
                if len(set(less_recent).intersection(more_recent)) > 0:
                    batch += [(clean_message, struct_message, 'weird_comparison') for clean_message, struct_message in
                              communicator.realise(data='intersection', intent='weird_comparison')]
                elif len(less_recent) != len(more_recent):
                    batch += [(clean_message, struct_message, 'weird_comparison') for clean_message, struct_message in
                              communicator.realise(data='etherogeneous_comparison', intent='weird_comparison')]
                elif less_recent[-1] + datetime.timedelta(days=1) != more_recent[0]:
                    batch += [(clean_message, struct_message, 'weird_comparison') for clean_message, struct_message in
                              communicator.realise(data='distant_dates', intent='weird_comparison')]

                data = dhl.compare(username, less_recent, more_recent, nutrients)

                # handling processing errors returned from DHL
                if data == 'mfp_error':
                    return slot_reset() + [ActionExecuted("action_listen")] + \
                        [UserUttered("/mfp_error", {"intent": {"name": "mfp_error", "confidence": 1.0}})]
                elif type(data) == str:
                    ActionEmptyMessageStack.silent(self, tracker.sender_id)
                    batch += [(clean_message, struct_message, data) for clean_message, struct_message in
                              communicator.realise(intent=data)]
                    message_stack[tracker.sender_id].append(batch)
                    return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
                else:
                    refined_data = communicator.prepare_data(data, 'compare')

                    if any(d['shrinked'] for d in [data['less_recent'], data['more_recent']]):
                        data['shrinked'] = sum([data[t]['shrinked'] for t in ['less_recent', 'more_recent'] if
                                                data[t]['shrinked'] != False], [])

                        batch += [(clean_message, struct_message, 'holes_surrounding_warn') for clean_message, struct_message in
                                  communicator.realise(data=data['shrinked'], intent='holes_surrounding_warn')]
                        message_stack[tracker.sender_id].append(batch)
                    if any(d['MI'] for d in [data['less_recent'], data['more_recent']]) and more_info:
                        print('more info denied')
                        # ActionEmptyMessageStack.silent(self, tracker.sender_id)
                        # batch += [(clean_message, struct_message, result) for clean_message, struct_message in
                        #         communicator.realise(intent=result)]
                        # message_stack[tracker.sender_id].append(batch)
                    
                        # return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
                        # ActionEmptyMessageStack.silent(self, tracker.sender_id)
                        # batch += [(clean_message, struct_message, 'more_info_denied') for clean_message, struct_message in
                        #            communicator.realise(intent='more_info_denied')]
                        # message_stack[tracker.sender_id].append(batch)
                        # return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
                        return "more_info_denied"  # TODO: delete message_stack, global slots and use communicator to return the output
                    elif any(d['MI'] for d in [data['less_recent'], data['more_recent']]):
                        # COMPARE AFTER ESTIMATING SOME DAYS
                        print('comparison after days estimated')
                        batch += [(clean_message, struct_message, None) for clean_message, struct_message in
                                  communicator.realise(data=data, intent='compare')]
                        message_stack[tracker.sender_id].append(get_imputation_button())
                        message_stack[tracker.sender_id].append(batch)
                        return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
                    else:
                        if more_info or adv_insight:
                            # MORE INFO AFTER COMPARE
                            print('more info after comparison')
                            for nutrient in nutrients:
                                temp_data = data
                                temp_data['keys'] = [nutrient]
                                temp_refined_data = refined_data
                                temp_refined_data['less_recent']['keys'] = [nutrient]
                                temp_refined_data['more_recent']['keys'] = [nutrient]
                                percentages = [[perc for perc in [d['budget'][nutrient]['goal_percentage'] for d in
                                                                  data['less_recent']['days']]],
                                               [perc for perc in [d['budget'][nutrient]['goal_percentage'] for d in
                                                                  data['more_recent']['days']]]]
                                charts = [
                                    {'type': 'chart',
                                     'content': {'chart_type': 'line',
                                                 'chart_name': 'CHART_INTAKE',
                                                 'args': {
                                                     'percentages': percentages,
                                                     'thresholds': temp_data['threshold'],
                                                     'data': refined_data,
                                                     'key': nutrient,
                                                     'quantify': False
                                                 }}
                                     },
                                    {'type': 'chart',
                                     'content': {'chart_type': 'trend',
                                                 'chart_name': 'CHART_TREND',
                                                 'args': {'percentages': percentages,
                                                          'thresholds': temp_data['threshold'],
                                                          'data': refined_data,
                                                          'key': nutrient,
                                                          'quantify': False
                                                          }
                                                 }
                                     },
                                    {'type': 'chart',
                                     'content': {'chart_type': 'pie',
                                                 'chart_name': 'CHART_FOOD',
                                                 'args': {'foods_lists': [
                                                     temp_refined_data['more_recent']['diet'][nutrient]['foods'],
                                                     temp_refined_data['less_recent']['diet'][nutrient]['foods']],
                                                          'key': nutrient,
                                                          'quantify': False
                                                          }
                                                 }
                                     }]
                                data['adv_insight'] = adv_insight
                                individual_batch = [(clean_message, struct_message, 'compare', nutrient) for clean_message, struct_message in
                                                    communicator.realise(data=temp_data, intent='compare',
                                                                         more_info=True)]
                                individual_batch = incorporate_charts(charts, individual_batch)
                                # gets the mapping keys that produces a non-empty set together with the adv_insight specified by the user, then converts each one to the respective value (indexes)
                                if adv_insight:
                                    indexes = list(map(lambda k: adv_insight_mappings[k],
                                                       list(filter(
                                                           lambda k: len(set(adv_insight).intersection(set(k))) != 0,
                                                           adv_insight_mappings.keys())
                                                            )
                                                       )
                                                   )[0]
                                    individual_batch = [individual_batch[i] for i in indexes]
                                    if len(nutrients) > 1 and nutrient != nutrients[-1]:
                                        individual_batch += get_more_info_button(nutrients[nutrients.index(nutrient)+1])
                                batch += individual_batch
                                if not adv_insight:
                                    message_stack[tracker.sender_id].append(get_content_filter_button(nutrient, more_info_filter))
                                message_stack[tracker.sender_id].append(batch)
                                batch = []
                            return [] if not adv_insight else ActionTriggerDeliver.run(self, dispatcher, tracker,
                                                                                       domain)
                        # REGULAR COMPARE
                        print('regular comparison')
                        batch += [(clean_message, struct_message, None) for clean_message, struct_message in
                                  communicator.realise(data=data, intent='compare')]
                        message_stack[tracker.sender_id].append(batch)

        return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)

class ActionShowPreferences(Action):
    def name(self) -> Text:
        return 'action_show_preferences'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0

        preferences = upl.dumps(username)
        dispatcher.utter_message(text=f'{preferences}')
        return []

class ActionTriggerDeliver(Action):
    def name(self) -> Text:
        return "action_trigger_deliver"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global deliver_flow, block_delivery, message_stack, current_batch

        if message_stack[tracker.sender_id] != []:
            current_batch[tracker.sender_id] += message_stack[tracker.sender_id].pop(0)
        else:
            return []
        block_delivery = False
        deliver_flow[tracker.sender_id] = []

        return slot_reset() + [ActionExecuted("action_listen")] \
               + [UserUttered("/delivery_intent", {"intent": {"name": "delivery_intent",  "confidence": 1.0}})]

class ActionDeleteButton(Action):
    def name(self) -> Text:
        return "action_delete_button"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global aux_bot

        chat_id = tracker.latest_message['metadata']['callback_query']['message']['chat']['id']
        message_id = tracker.latest_message['metadata']['callback_query']['message']['message_id']

        aux_bot.delete_message(chat_id, message_id)

    def delete_arbitrary(self, chat_id, message_id):
        global aux_bot

        aux_bot.delete_message(chat_id, message_id)

class ActionDeliverMessage(Action):
    def name(self) -> Text:
        return "action_deliver_message"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global wait_time, deliver_flow, message_stack, current_batch, block_delivery
        if block_delivery:
            return []

        if len(current_batch[tracker.sender_id]) == 0:
            block_delivery = True
        else:
            message = current_batch[tracker.sender_id].pop(0)
            deliver_flow[tracker.sender_id].append(message)
            clean = message[0] if type(message) == tuple else message
            sleep(wait_time)
            wait_time = len([clean]) * 0.10 * (len(clean.split()) if isinstance(clean, str) else 8)
            self.process_message(message, tracker, dispatcher)
            if len(current_batch[tracker.sender_id]) == 0:
                wait_time = 0
        return []

    def process_message(self, message, tracker, dispatcher):
        clean = message[0] if type(message) == tuple else message
        struct = message[1] if type(message) == tuple else None
        intent = message[2] if type(message) == tuple and len(message) > 2 else None
        nutrient = message[3] if type(message) == tuple and len(message) > 3 else None

        if type(clean) == dict and clean != {}:
            if clean['type'] == 'chart':
                args = clean['content']['args']
                chart_type = clean['content']['chart_type']
                if chart_type == 'line':
                    plot = dhl.data_visualization_module.line_chart(**args)
                    chart_name = f'share/line_{tracker.sender_id}.png'
                elif chart_type == 'trend':
                    plot = dhl.data_visualization_module.trend_chart(**args)
                    chart_name = f'share/line_{tracker.sender_id}.png'
                elif chart_type == 'pie':
                    plot = dhl.data_visualization_module.food_chart(**args)
                    chart_name = f'share/pie_{tracker.sender_id}.png'
                try:
                    plot.savefig(chart_name, bbox_inches='tight')
                    dispatcher.utter_message(image=chart_name)
                    # os.remove(chart_name)
                except:  # case in which the chart can't be produced (too few data), the layer produces an error message instead
                    dispatcher.utter_message(text = plot) #this is useless but removing it messes up the stack by removing a message, TODO handle
            elif clean['type'] == 'button':
                output = clean['content']['text']
                if tracker.get_slot('rephrasing') and intent and (
                        (intent not in ['compare', 'empty_more_info', 'filter_more_info_button', 'partial_typo', 'unauthorised_user', 'update']) \
                        or (intent in ['update', 'compare']) \
                        or ('CHART' not in intent)):
                    try:
                        print('rephrasing:', tracker.get_slot('rephrasing'))
                        rephrased_output = rephrase(output, intent, nutrient)
                        dispatcher.utter_message(text=rephrased_output,
                                                 buttons=clean['content']['buttons'],
                                                 button_type=clean['content']['button_type'])
                        return
                    except:
                        pass
                dispatcher.utter_message(text=output,
                                         buttons=clean['content']['buttons'],
                                         button_type=clean['content']['button_type'])
            else:
                output = clean['content']
                if tracker.get_slot('rephrasing') and intent and (
                        (intent not in ['compare', 'empty_more_info', 'filter_more_info_button', 'partial_typo', 'unauthorised_user', 'update']) \
                        or (intent in ['update', 'compare']) \
                        or ('CHART' not in intent)):
                    try:
                        print('rephrasing:', tracker.get_slot('rephrasing'))
                        rephrased_output = rephrase(output, intent, nutrient)
                        dispatcher.utter_message(rephrased_output)
                        return
                    except:
                        pass
                dispatcher.utter_message(output)


class ActionEmptyMessageStack(Action):
    def name(self) -> Text:
        return "action_empty_message_stack"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global message_stack, current_batch, deliver_flow, wait_time, more_info_exhausted

        message_stack[tracker.sender_id] = []
        current_batch[tracker.sender_id] = []
        deliver_flow[tracker.sender_id] = []
        wait_time = 0
        more_info_exhausted = False

        return slot_reset()

    def silent(self, sender_id):
        global message_stack, current_batch
        global wait_time
        global more_info_exhausted
        message_stack[sender_id] = []

        wait_time = 0
        more_info_exhausted = False
        return slot_reset()

class ActionEmptyMessageStackOnButton(Action):
    def name(self) -> Text:
        return "action_empty_message_stack_on_button"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global message_stack, current_batch, deliver_flow, more_info_filter, aux_bot, wait_time, more_info_exhausted

        batch = []
        chat_id = tracker.latest_message['metadata']['callback_query']['message']['chat']['id']
        message_id = tracker.latest_message['metadata']['callback_query']['message']['message_id']

        aux_bot.delete_message(chat_id, message_id)

        message_stack[tracker.sender_id] = []
        current_batch[tracker.sender_id] = []
        deliver_flow[tracker.sender_id] = []
        wait_time = 0
        more_info_exhausted = False
        more_info_filter = set()

        # TODO: put this into a template with proper slots
        batch += [(clean_message, struct_message, 'empty_message_stack') for clean_message, struct_message in
                  communicator.realise(intent='empty_message_stack')]
        message_stack[tracker.sender_id].append(batch)

        return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)

class ActionExhaustLeftoverMessages(Action):  # useful for when an interaction gets interrupted by the user
    def name(self) -> Text:
        return "action_exhaust_leftover_messages"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global message_stack, wait_time, more_info_exhausted, current_batch, more_info_filter, deliver_flow, block_delivery

        message_stack[tracker.sender_id] = []
        current_batch[tracker.sender_id] = []
        wait_time = 0
        more_info_exhausted = False
        more_info_filter = set()

class ActionWaitPlease(Action):
    def name(self) -> Text:
        return "action_wait_please"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0
        print('\n**********WAIT PLEASE**********')
        
        data = tracker
        print('wait entities:', data.latest_message['entities'])
        
        action_deliver = ActionDeliverMessage()  # TODO substitute with classic ActionTriggerDeliver call
        for clean_message, struct_message in communicator.realise(data=data, intent='wait'):
            action_deliver.process_message((clean_message, struct_message, 'wait'), tracker, dispatcher)

class ActionWaitMorePlease(Action):
    def name(self) -> Text:
        return "action_wait_more_please"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0
        print('\n**********WAIT MORE PLEASE**********')

        action_deliver = ActionDeliverMessage()
        for clean_message, struct_message in communicator.realise(intent='wait_more'):
            action_deliver.process_message((clean_message, struct_message, 'wait_more'), tracker, dispatcher)

class ActionFilterMoreInfo(Action):
    def name(selfs) -> Text:
        return "action_filter_more_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global more_info_filter, message_stack, last_action, aux_bot

        if len(tracker.latest_message['entities']) > 0:  # normal filter action: the user pressed the submit button
            chosen_button = set(int(el) for el in tracker.latest_message['entities'][0]['value'])

            if all(i in more_info_filter for i in chosen_button):
                more_info_filter = more_info_filter - chosen_button
            else:
                more_info_filter |= set(chosen_button)

            chat_id = tracker.latest_message['metadata']['callback_query']['message']['chat']['id']
            message_id = tracker.latest_message['metadata']['callback_query']['message']['message_id']

            more_info_filter = set(sorted(more_info_filter))

            aux_bot.delete_message(chat_id, message_id)
            last_message = [''.join(filter(str.isalnum, x)) for x in str(tracker.latest_message['metadata']['callback_query']['message']['text']).lower().split(" ")]
        slot = list(filter(lambda x: x in nutrients_lookup, last_message))[0]
        message_stack[tracker.sender_id].insert(0, get_content_filter_button(slot, more_info_filter))

        return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)

class ConfirmFilterMoreInfo(Action):
    def name(selfs) -> Text:
        return "action_confirm_filter_more_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global more_info_filter, message_stack, current_batch, last_action
        ActionDeleteButton.run(self, dispatcher, tracker, domain)
        try:
            indexes = list(more_info_mappings.values())
            indexes = [indexes[i] for i in more_info_filter]
            indexes = set(itertools.chain(*indexes))  # flattening list
            
            if type(message_stack[tracker.sender_id][0][0]) == tuple and message_stack[tracker.sender_id][0][0][-1] == 'weird_comparison':
                message_stack[tracker.sender_id][0] = [message_stack[tracker.sender_id][0][0]] + [message_stack[tracker.sender_id][0][i+1] for i in indexes]
            else:
                message_stack[tracker.sender_id][0] = [message_stack[tracker.sender_id][0][i] for i in indexes]
            # message_debug_print(message_stack[tracker.sender_id])
            
            curr_nutrient = None
            next_nutrient = None
            if len(message_stack[tracker.sender_id]) > 1:
                nutrients = nutrients_lookup[:1] + nutrients_lookup[2:] # disregard calories at index 1
                for message in message_stack[tracker.sender_id][0]:
                    if type(message) == dict:
                        curr_nutrient = message['content']['args']['key']
                    elif type(message) == tuple:
                        curr_nutrient = message[-1]
                    else:
                        curr_nutrient = None
                    
                    if curr_nutrient and curr_nutrient in nutrients:
                        break
                
                if curr_nutrient and curr_nutrient in nutrients:
                    next_nutrient = nutrients[nutrients.index(curr_nutrient)+1]
                message_stack[tracker.sender_id][0] += get_more_info_button(next_nutrient)

        except Exception as e:
            print(f'ERROR WHILE VALIDATING FILTER_MORE_INFO: {e}')
            message_stack[tracker.sender_id].insert(0,[(clean_message, struct_message, 'invalid_button') for clean_message, struct_message in communicator.realise(intent='invalid_button')])

        more_info_filter = set(sorted(more_info_filter))
        more_info_filter = set()

        return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)

class ActionQuantify(Action):
    def name(self) -> Text:
        return "action_quantify"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0

        global message_stack, deliver_flow

        batch = []
        quantify = True if tracker.slots['quantify'] == 'quantify_on' else False

        tracker.slots['quantify'] = None

        if len(deliver_flow[tracker.sender_id]) == 0:
            dispatcher.utter_message('nothing to quantify, sorry!')
            return []

        # finding latest user message
        for event in list(reversed(tracker.events))[:(100 if len(tracker.events) >= 100 else len(tracker.events) - 1)]:
            if 'metadata' in event and event['metadata'] != {}:
                try:
                    # getting message_id
                    chat_id = event['metadata']['callback_query']['message']['chat']['id']
                    message_id = event['metadata']['callback_query']['message']['message_id']
                    text = event['metadata']['callback_query']['message']['text']
                # in some cases 'callback_query' key is not present
                except:
                    chat_id = event['metadata']['message']['chat']['id']
                    message_id = event['metadata']['message']['message_id']
                    text = event['metadata']['message']['text']
                break


        # getting the amount of messages sent last time and deleting them
        messages_n = len(deliver_flow[tracker.sender_id])
        for i in range(message_id - (messages_n + 1), message_id + 2):
            try:
                aux_bot.delete_message(chat_id, i)
            except:
                pass
        batch += [p for p in communicator.realise(data=deliver_flow[tracker.sender_id], skip_data=True, quantify=quantify)]

        message_stack[tracker.sender_id].insert(0, batch)
        return []

class ActionMoreInfo(Action):
    def name(self) -> Text:
        return "action_more_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        username = ActionVerifyAccess.verify(self, dispatcher, tracker)
        if not username:
            return 0
        
        print('\n**********MORE INFO**********')

        global more_info_exhausted, target_class, last_action
        if more_info_exhausted:
            more_info_exhausted = False
            print('More info hallucinated, aborting')
            return []
        else:
            print('More info seems legit, proceeding')
        batch = []

        last_action, last_intent_struct = extract_last_action(tracker)
        if not last_action:
            last_action = 'update'
            last_intent_struct = {}

        tracker_backup = copy.deepcopy(tracker)
        tracker_backup.latest_message = last_intent_struct

        print('more info tracker slots:', tracker.slots)

        # for slot in ['nutrient', 'time']:
        #     if tracker.slots[slot] and len(tracker.slots[slot]) > 0:
        #         if slot == 'nutrient':
        #             tracker.slots[slot] = sort_nutrients(tracker.slots[slot])
        #         tracker_backup.slots.update({slot: tracker.slots[slot]})
        #         print(f'tracker {slot} slot:', tracker.slots[slot])
        #     else:
        #         try:
        #             entities = last_intent_struct['entities']
        #             # duckling_entities = [entity for entity in entities if entity['extractor'] == 'DucklingEntityExtractor']
        #             # other_entities = [entity for entity in entities if entity['extractor'] != 'DucklingEntityExtractor']
        #             # if len(entities) > 2 \
        #             #         or len(entities) == 2 and other_entities and duckling_entities[0]['text'] == other_entities[0]['value']:
        #             #     entities = duckling_entities
        #             # print('entities:', tracker_backup.latest_message['entities'])
        #             entity = list(filter(lambda x: (x['entity'] == slot), entities))[0]
        #             tracker_backup.slots.update({slot: entity['value']})
        #         except:
        #             tracker_backup.slots.update({slot: []})  # in case the slot wasn't specified (e.g.: nutrient not specified, so all are selected)
        
        entities = last_intent_struct['entities'] if 'entities' in last_intent_struct else []
        print('more info entities:', entities)

        time_entities = list(filter(lambda x: (x['entity'] == 'time'), entities))
        print('time entities:', time_entities)
        if len(time_entities) == 0 and tracker.slots['time'] and len(tracker.slots['time']) > 0:
            tracker_backup.slots.update({'time': tracker.slots['time']})
        elif len(time_entities) == 1 and 'value' in time_entities[0]:
            tracker_backup.slots.update({'time': time_entities[0]['value']})
        elif len(time_entities) == 2 and 'value' in time_entities[0] and 'value' in time_entities[1]:
            tracker_backup.slots.update({'time': [entity['value'] for entity in time_entities]})
        try:
            tracker_backup.slots.update({'time': [entity['value'] for entity in time_entities]})
        except:
            if tracker.slots['time']:
                tracker_backup.slots.update({'time': tracker.slots['time']})
            else:
                tracker_backup.slots.update({'time': []})

        nutrient_entity = list(filter(lambda x: (x['entity'] == 'nutrient'), entities))
        print('nutrient entity:', nutrient_entity)
        if nutrient_entity:
            tracker_backup.slots.update({'nutrient': nutrient_entity[0]['value']})
        elif tracker.slots['nutrient'] and len(tracker.slots['nutrient']) > 0:
                tracker.slots['nutrient'] = sort_nutrients(tracker.slots['nutrient'])
                tracker_backup.slots.update({'nutrient': tracker.slots['nutrient']})
        else:
            tracker_backup.slots.update({'nutrient': []})

        if tracker_backup.slots['nutrient'] == 'preferences' or tracker_backup.slots['nutrient'] == []:
            tracker_backup.slots['nutrient'] = upl.dumps(username)['keys']
            tracker_backup.slots['nutrient'] = sort_nutrients(tracker_backup.slots['nutrient'])

        tracker_backup.slots.update({"more_info": True})
        my_class = None
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj):
                obj_cleaned = str(obj).replace('\'', '').replace(' ', '').replace('class', '').replace('<', '').replace(
                    '>', '')
                my_class = locate(obj_cleaned)
                try:
                    if (my_class.name(self) == last_action):
                        break
                    else:
                        my_class = None
                except:
                    continue
        if(my_class):
            if isinstance(tracker_backup.slots['nutrient'], str):
                tracker_backup.slots['nutrient'] = [tracker_backup.slots['nutrient']]
            try:
                print('my_class:', my_class)
                result = my_class.run(self, dispatcher, tracker_backup, domain)
                if type(result) == str and type(result) != list:
                    ActionEmptyMessageStack.silent(self, tracker.sender_id)
                    batch += [(clean_message, struct_message, result) for clean_message, struct_message in
                            communicator.realise(intent=result)]
                    message_stack[tracker.sender_id].append(batch)
                print('result:', result)
                return ActionTriggerDeliver.run(self, dispatcher, tracker, domain)
            except:
                return slot_reset() + [ActionExecuted("action_listen")] \
                        + [UserUttered("/out_of_scope", {"intent": {"name": "out_of_scope", "confidence": 1.0}})]

class ActionSetContext(Action):
    def name(self) -> Text:
        return "action_set_context"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        latest_intent = tracker.get_intent_of_latest_message()
        return [SlotSet("context", latest_intent), SlotSet("more_info", latest_intent=="more_info")]
    
class ActionAskCounselling(Action):
    def name(self) -> Text:
        return "action_ask_counselling"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = get_counselling_buttons()[0]
        if tracker.slots['rephrasing']:
            message['content']['text'] = rephrase(message['content']['text'], 'counselling')
        return dispatcher.utter_message(text=message['content']['text'],
                                        buttons=message['content']['buttons'],
                                        button_type=message['content']['button_type'])

class ActionRetryCounselling(Action):
    def name(self) -> Text:
        return "action_retry_counselling"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = get_retry_counselling_buttons()[0]
        if tracker.slots['rephrasing']:
            message['content']['text'] = rephrase(message['content']['text'], 'retry_counselling')
        return dispatcher.utter_message(text=message['content']['text'],
                                        buttons=message['content']['buttons'],
                                        button_type=message['content']['button_type'])

class ActionResetStruggleForm(Action): 	
    def name(self): 		
        return "action_reset_struggle_form"
	
    def run(self, dispatcher, tracker, domain):
        return [SlotSet("struggle", None), SlotSet("refl_response", None)]

class ActionAskReflResponse(Action):
    def name(self) -> Text:
        return "action_ask_refl_response"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global counselling_texts, counselling_turn_count
        
        struggle = tracker.get_slot('struggle')
        # with torch.inference_mode():
        #     input_ids = counselling_tokenizer(TASK_PREFIXES['reflection'] + struggle, return_tensors='pt').to(DEVICE).input_ids
        #     output_ids = counselling_model.generate(input_ids,
        #                                             max_new_tokens=100,
        #                                             pad_token_id=counselling_tokenizer.eos_token_id,
        #                                             do_sample=True,
        #                                             temperature=0.3,
        #                                             top_p=0.9)
        #     reflection = counselling_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        reflection = generate_counselling_response(struggle, 'reflection')

        counselling_texts[tracker.sender_id] = {
            'struggle': struggle,
            'reflection': reflection,
            'comfort': '',
            'reframing': '',
            'suggestion': ''
        }

        dispatcher.utter_message(text=reflection)

        return []

class ActionAddReflElaboration(Action):
    def name(self) -> Text:
        return "action_add_refl_elaboration"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        struggle = tracker.get_slot('struggle')
        elaboration = tracker.latest_message['text']

        return [ActionReverted(), ActionReverted(), SlotSet('struggle', struggle + ' ' + elaboration), SlotSet('refl_response')]

class ActionProvideComfort(Action):
    def name(self) -> Text:
        return "action_provide_comfort"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global counselling_texts

        struggle = tracker.get_slot('struggle')
        # with torch.inference_mode():
        #     input_ids = counselling_tokenizer(TASK_PREFIXES['comfort'] + struggle, return_tensors='pt').to(DEVICE).input_ids
        #     output_ids = counselling_model.generate(input_ids,
        #                                             max_new_tokens=100,
        #                                             pad_token_id=counselling_tokenizer.eos_token_id,
        #                                             do_sample=True,
        #                                             temperature=0.3,
        #                                             top_p=0.9)
        #     comfort = counselling_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        comfort = generate_counselling_response(struggle, 'comfort')

        counselling_texts[tracker.sender_id]['comfort'] = comfort
        dispatcher.utter_message(text=comfort)

        return []

class ActionProvideReframing(Action):
    def name(self) -> Text:
        return "action_provide_reframing"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global counselling_texts

        struggle = tracker.get_slot('struggle')
        # with torch.inference_mode():
        #     input_ids = counselling_tokenizer(TASK_PREFIXES['reframing'] + struggle, return_tensors='pt').to(DEVICE).input_ids
        #     output_ids = counselling_model.generate(input_ids,
        #                                             max_new_tokens=100,
        #                                             pad_token_id=counselling_tokenizer.eos_token_id,
        #                                             do_sample=True,
        #                                             temperature=0.3,
        #                                             top_p=0.9)
        #     reframing = counselling_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        reframing = generate_counselling_response(struggle, 'reframing')

        counselling_texts[tracker.sender_id]['reframing'] = reframing
        dispatcher.utter_message(text=reframing)
        sleep(1)

        return []

class ActionProvideSuggestion(Action):
    def name(self) -> Text:
        return "action_provide_suggestion"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        struggle = tracker.get_slot('struggle')
        # with torch.inference_mode():
        #     input_ids = counselling_tokenizer(TASK_PREFIXES['suggestion'] + struggle, return_tensors='pt').to(DEVICE).input_ids
        #     output_ids = counselling_model.generate(input_ids,
        #                                             max_new_tokens=100,
        #                                             pad_token_id=counselling_tokenizer.eos_token_id,
        #                                             do_sample=True,
        #                                             temperature=0.3,
        #                                             top_p=0.9)
        #     suggestion = counselling_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        suggestion = generate_counselling_response(struggle, 'suggestion')

        counselling_texts[tracker.sender_id]['suggestion'] = suggestion
        dispatcher.utter_message(text=suggestion)
        sleep(1)

        return []

class ActionAskFeedback(Action):
    def name(self) -> Text:
        return "action_ask_feedback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = get_feedback_buttons()[0]
        return dispatcher.utter_message(text=message['content']['text'],
                                        buttons=message['content']['buttons'],
                                        button_type=message['content']['button_type'])

class ActionSaveFeedback(Action):
    def name(self) -> Text:
        return "action_save_feedback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.latest_message['intent'].get('name')
        if intent == 'deny':
            intent = 'negative_feedback'

        counselling_texts[tracker.sender_id]['feedback'] = intent
        with open('feedback.csv', 'a', newline='') as f:
            keys = ['struggle', 'reflection', 'comfort', 'reframing', 'suggestion', 'feedback']
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writerow(counselling_texts[tracker.sender_id])

        return []
    
class ActionNotifyPromptFillDiary(Action):
    def name(self) -> Text:
        return "action_notify_prompt_fill_diary"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        admin_user = 'saeshyra'
        admin_sender_id = upl.preferences_management_module.get_user_from_db(telegram_user=admin_user)[3]

        telegram_user = next(tracker.get_latest_entity_values('telegram_user'), None)

        if tracker.sender_id == admin_sender_id:
            dispatcher.utter_message(f'Prompted {telegram_user} to fill their empty food diary')

        return []

class ActionNotifyPromptCheckDiary(Action):
    def name(self) -> Text:
        return "action_notify_prompt_check_diary"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        admin_user = 'saeshyra'
        admin_sender_id = upl.preferences_management_module.get_user_from_db(telegram_user=admin_user)[3]

        telegram_user = next(tracker.get_latest_entity_values('telegram_user'), None)

        if tracker.sender_id == admin_sender_id:
            dispatcher.utter_message(f'Prompted {telegram_user} to check their abnormal food diary')

        return []
    
class ActionNotifyPromptInteract(Action):
    def name(self) -> Text:
        return "action_notify_prompt_interact"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        admin_user = 'saeshyra'
        admin_sender_id = upl.preferences_management_module.get_user_from_db(telegram_user=admin_user)[3]

        telegram_user = next(tracker.get_latest_entity_values('telegram_user'), None)

        if tracker.sender_id == admin_sender_id:
            dispatcher.utter_message(f'Prompted {telegram_user} to interact with chatbot')

        return []
    
class ActionCheckDiary(Action):
    def name(self) -> Text:
        return "action_check_diary"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        _, mfp_user, _, _, _, _ = upl.preferences_management_module.get_user_from_db(sender_id=tracker.sender_id)

        abnormality = dhl.check_diary(mfp_user)
        if abnormality == 'empty':
            text = "Hey! I noticed that your food diary from yesterday is still empty... It's important to log your foods while you still remember what you've eaten!"
        elif abnormality == 'no mfp access':
            text = "Hmm... I can't seem to access your food diary on MyFitnessPal. Double check that you've set Diary Sharing to Friends!"
        elif abnormality:
            text = "Hey! I noticed {} in your food diary yesterday... Maybe double check to see if everything's logged correctly?".format(abnormality)
        else:
            return []
        
        if tracker.slots['rephrasing'] and abnormality != 'no mfp access':
            text = rephrase(text, intent='check_diary')

        with open('abnormal_diaries.csv', 'a', newline='') as f:
            keys = ['date', 'mfp_user', 'abnormality']
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writerow({'date': (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%m-%Y"),
                                  'mfp_user': mfp_user,
                                  'abnormality': abnormality})

        buttons = get_check_diary_buttons()[0]
        return dispatcher.utter_message(text=text,
                                        buttons=buttons['content']['buttons'],
                                        button_type=buttons['content']['button_type'])

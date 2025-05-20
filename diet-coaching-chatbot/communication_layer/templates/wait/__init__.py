from actions.actions import extract_periods
import user_profiling_layer as upl

#TODO: handle trend, food analysis etc...
def prepare_data(raw_data, communicator):
    slots = raw_data.slots

    nutrients = [entity['value'] for entity in list(filter(lambda x: x['entity'] == 'nutrient', raw_data.latest_message['entities']))]
    adv_insight = [entity['value'] for entity in list(filter(lambda x: x['entity'] == 'adv_insight', raw_data.latest_message['entities']))]
    context = slots['context']
    if nutrients == []:
        nutrients = 'preferences'
    elif len(nutrients) > 1:
        nutrients = communicator.inflect_list(nutrients)
    else:
        nutrients = str(nutrients[0])

    if len(adv_insight) > 0:
        if len(adv_insight) > 1:
            adv_insight = communicator.inflect_list(adv_insight)
        else:
            adv_insight = str(adv_insight[0])
    else:
        adv_insight = []

    def wordify(t):
        return f'{"{:%b %d %Y}".format(t)}'
    
    _, _, _, _, _, timezone = upl.preferences_management_module.get_user_from_db(sender_id=raw_data.sender_id)

    time_entities = list(filter(lambda x: (x['entity'] == 'time'), raw_data.latest_message['entities']))
    time = extract_periods(time_entities, (1 if context=='update' else 2), timezone)
    if time and time[0]:
        time = [f'from {wordify(t[0])}'+(f' to {wordify(t[-1])}' if len(t)>1 else '') for t in time]
        return {'time':time,'nutrients':nutrients, 'context':context, 'adv_insight':adv_insight}

    return None

import pprint
from jinja2 import Environment, FileSystemLoader
import random
from datetime import datetime
import inflect
from importlib import import_module
import os
import requests
import json
import communication_layer

class Communicator:

    def __init__(self):
        self.prev_random = -1

    def inflect_list(self, l):
        if len(l) == 1:
            return l[0]
        eng = inflect.engine()
        return eng.join(l)

    def smart_random(self, slots):
        if len(slots) == 1:
            return slots[0]
        n = self.prev_random
        while(n == self.prev_random):
            n = random.randint(0,len(slots)-1)

        self.prev_random = n
        return slots[n]

    def capitalize_fst(self, text):
        return ''+text[0].upper()+text[:1]

    def wordify_date(self, raw_date, *day_only):
        wordified_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%B %d")
        if (day_only):
            wordified_date = wordified_date.split(' ')[1]
        return wordified_date

    def count_days(self, start, end):
        return (datetime.strptime(start, "%Y-%m-%d") - datetime.strptime(end, "%Y-%m-%d")).days + 1

    def prepare_data(self, raw_data, intent):
        module = 'communication_layer.templates.' + intent
        data_parser = import_module(module)
        return data_parser.prepare_data(raw_data, self)

    def realise(self, data={}, intent=None, more_info=False, quantify=False, skip_data=False):
        env = Environment(loader=FileSystemLoader(os.getcwd()))
        templates_main_path = '/communication_layer/templates/'

        env.trim_blocks = True
        env.lstrip_blocks = True
        env.filters['smart_random'] = self.smart_random
        env.filters['capitalize_fst'] = self.capitalize_fst
        env.filters['inflect_lst'] = self.inflect_list
        env.add_extension('jinja2.ext.do')

        if skip_data:
            struct_output = [d[1] if type(d)==tuple else d for d in data]
        else:
            int_template = env.get_template(templates_main_path + intent + '/' + (intent + '.j2' if not more_info else 'more.j2'))
            data = {"data": self.prepare_data(data, intent)}
            if intent == 'wait' and data['data'] is None:
                return []
            env.globals['env'] = globals()
            struct_output = [{'type':'text','content': m} for m in int_template.render(data).split('<<--->>')]
            struct_output = list(filter(lambda x: not (type(x['content']) == str and x['content'].isspace()), struct_output)) #probably useless after fixing spaces etc..
        textf = communication_layer.text_formatter.TextFormatterUtility()
        final_output = []
        for struct_line in struct_output:
            if type(struct_line) == str or (type(struct_line) == dict and struct_line['type'] != 'text'):
                if struct_line['type'] == 'chart':
                        struct_line['content']['args']['quantify'] = quantify
                final_output.append((struct_line,struct_line))
            elif struct_line:  # order is important! Emojification must be ran before
                line = " ".join(struct_line['content'].split())
                line = textf.emojification(line)
                line = textf.format(line)
                line = textf.handle_whitespaces(line)
                line = textf.quantification(line) if quantify else textf.quantification(line, keep_numbers=True)
                # print('| line quantified:', line)
                if type(line) != bool:
                    final_output.append(({'type':'text','content':line.strip()},struct_line))
        return final_output
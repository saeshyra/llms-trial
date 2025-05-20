import pickle
import os
import numpy as np
import pandas as pd
from torch.utils.data import Dataset

TEXT_TYPES = ['struggle', 'reflection', 'comfort', 'reframing', 'suggestion']
SPECIAL_TOKENS = ['<|struggle|>', '<|reflection|>', '<|comfort|>', '<|reframing|>', '<|suggestion|>', '<|endoftext|>']
TASK_PREFIXES = {'V1': {'reflection': 'Below is a diet struggle. Provide a reflection to understand what they mean.',
                        'comfort':    'Below is a diet struggle. Provide comfort to explain how it is normal to experience.',
                        'reframing':  'Below is a diet struggle. Provide some reframing to tell them how to see it in a more positive way.',
                        'suggestion': 'Below is a diet struggle. Provide a suggestion on how they can face the struggle.'},
                 'V2': {'reflection': 'Summarize what the problem is about or infer what they mean. Do not assume their feelings.',
                        'comfort':    'Tell them that the situation is not unrecoverable, normalize the situation or make them feel understood. Do not normalize dangerous behaviours in a way that explicitly encourages your client to commit them.',
                        'reframing':  'Show a benefit to the struggle that they did not consider or find something about the struggle to be grateful for.',
                        'suggestion': 'Tell the person how to change their habit to improve or suggest an alternative helpful activity.'},
                 'T5': {'reflection': 'Provide a reflection to understand what they mean: ',
                        'comfort':    'Provide comfort to explain how it is normal to experience it: ',
                        'reframing':  'Provide some reframing to tell them how to see it in a more positive way: ',
                        'suggestion': 'Provide a suggestion on how they can face the struggle: '}}

class HAICoachingDataset(Dataset):

    def __init__(self, split, dataset_path=None, cache_dir='data/'):
        self.split = split
        print('DATASET TYPE:', self.split)

        # create cache dir if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.f_name = os.path.join(cache_dir, f"{split}_preprocessed_data.json")

        # if the dataset has already been preprocessed, load it from the cache
        if os.path.isfile(self.f_name):
            data = pickle.load(open(self.f_name, 'rb'))
            print(f"Loaded {len(data)} examples from cached file.")
        else:
            # read data values from csv
            if not dataset_path:
                dataset_path = 'data/dataset.xlsx'
            dataset = pd.read_excel(dataset_path, sheet_name='DATASET', keep_default_na=False)

            # split lists in columns with ### separator
            for col in dataset.columns:
                if type(dataset[col][0]) == str:
                    if dataset[col].str.contains(" ### ").any():
                        new_col = dataset[col].str.split(" ### ")
                        dataset[col] = new_col
            
            # train-valid-test split
            splits = np.split(dataset.sample(frac=1, random_state=42), [int(.8*len(dataset)), int(.9*len(dataset))])
            for i, split in enumerate(['train', 'validation', 'test']):
                if self.split == split:
                    dataset_split = splits[i]
                    
            if self.split == 'test':
                data = self.extract_references(dataset_split)
            else:
                data = self.extract_examples(dataset_split)
            self.save_data(data)
        self.data = data

    def save_data(self, data):
        assert not os.path.exists(self.f_name), f"{self.f_name} already exists."
        with open(self.f_name, 'wb+') as f:
            pickle.dump(data, f)

    def __getitem__(self, idx):
        return self.data[idx]

    def __len__(self):
        return len(self.data)
    
    def extract_examples(self, dataset):
        text_examples = []

        for i in dataset.index:
            # use only relevant struggles
            # if dataset['cluster_micro_expert'][i] != 'OT':
            if dataset['cluster_macro_expert'][i] != 'NOT_APPLICABLE':


                for text_type in TEXT_TYPES[1:]:
                    # use expert text if provided
                    for expert_text in dataset[text_type + '_from_expert'][i]:
                        if expert_text != 'N/A':
                            text_examples.append({'struggle': dataset['struggle'][i],
                                                  'text': expert_text,
                                                  'text_type': text_type})

                    else: # use first accepted text from candidates
                        for candidate_text, annotation in zip(dataset[text_type + '_candidates'][i],
                                                              dataset[text_type + '_annotation'][i]):
                            if annotation == 'Y':
                                text_examples.append({'struggle': dataset['struggle'][i],
                                                      'text': candidate_text,
                                                      'text_type': text_type})
                    
        return text_examples
    
    def extract_references(self, dataset):
        text_examples = []

        for i in dataset.index:
            # use only struggles within domain
            if dataset['cluster_micro_expert'][i] != 'OT':

                for text_type in TEXT_TYPES[1:]:
                    texts = []

                    for expert_text in dataset[text_type + '_from_expert'][i]:
                        if expert_text != 'N/A':
                            texts.append(expert_text)

                    for candidate_text, annotation in zip(dataset[text_type + '_candidates'][i],
                                                          dataset[text_type + '_annotation'][i]):
                        if annotation == 'Y':
                            texts.append(candidate_text)
                    
                    if texts:
                        text_examples.append({'struggle': dataset['struggle'][i],
                                              'texts': texts,
                                              'text_type': text_type})

        return text_examples
import argparse
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import evaluate
from sacrebleu.metrics import BLEU

from hai_coaching_dataset import HAICoachingDataset, TASK_PREFIXES
from datasets import Dataset

ap = argparse.ArgumentParser(description='Decode Llama 3 models train one 1 safe reference or all safe references from HAI-Coaching')

DEVICE = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
ap.add_argument('--model-id', default='meta-llama/Meta-Llama-3-8B', type=str, help='HuggingFace model to evaluate finetuned outputs of')


def main(args: argparse.Namespace):

    # finetuned_model_dir_old = f"{args.model_id}_finetuned_hai-coaching_v1"
    finetuned_model_dir_new = f"{args.model_id}_finetuned_hai-coaching_v2"

    # old_model = AutoModelForCausalLM.from_pretrained(finetuned_model_dir_old)
    new_model = AutoModelForCausalLM.from_pretrained(finetuned_model_dir_new)
    # old_model.to(DEVICE)
    new_model.to(DEVICE)
    # old_tokenizer = AutoTokenizer.from_pretrained(finetuned_model_dir_old)
    new_tokenizer = AutoTokenizer.from_pretrained(finetuned_model_dir_new)
    # old_model.eval()
    new_model.eval()
    
    def format_instruction_new(sample):
        return f"""    
You are an expert dietitian. Below is a struggle your client is experiencing. {TASK_PREFIXES['V2'][sample['text_type']]}

Struggle:
{sample['struggle']}

{sample['text_type'][0].upper()+sample['text_type'][1:]}:
"""
#     def format_instruction_old(sample):
#         return f"""    
# {TASK_PREFIXES['V1'][sample['text_type']]}

# ### Struggle:
# {sample['struggle']}

# ### {sample['text_type'][0].upper()+sample['text_type'][1:]}:
# """
    
    struggles = [
        "I eat when I'm stressed or emotional, and it affects my diet. How can I manage this?",
        "I've struggled with an eating disorder in the past and have difficulty maintaining a balanced diet.",
        "I have multiple food allergies and find it hard to get enough variety in my diet.",
        "I follow a vegan/gluten-free/keto diet, and I find it hard to meet my nutritional needs.",
        "I'm unhappy with my body and often skip meals to lose weight.",
        "I have a chronic illness that makes it hard to eat a regular diet.",
        "Healthy food is expensive, and I struggle to afford it on a tight budget.",
        "My family's traditional foods are not very healthy, but it's hard to avoid them without offending anyone.",
        "I rarely feel hungry and struggle to eat enough throughout the day.",
        "I have trouble controlling portion sizes and often overeat.",
        "I don't like the taste of most vegetables and find it hard to eat them.",
        "I'm a very picky eater and struggle to find healthy foods I enjoy.",
        "I don't always have access to enough food and have trouble planning a balanced diet.",
        "I have IBS and many foods upset my stomach.",
        "I rely on supplements for my nutrition and worry I'm not getting enough from actual food.",
        "I don't have enough time to prepare healthy meals.",
        "I am obsessed with eating only 'clean' or 'pure' foods and it's affecting my health.",
        "I find it hard to stick to my diet when eating out with friends or at social gatherings.",
        "I feel addicted to sugar/junk food and can't stop eating it.",
        "I have episodes of binge eating and then feel guilty and ashamed.",
        "I need to follow a low-sodium/low-carb/low-fat diet for medical reasons and find it challenging.",
        "I have a nutrient deficiency (like iron or vitamin D) and struggle to correct it with my diet.",
        "I'm pregnant/recently gave birth and finding it hard to eat a balanced diet.",
        "I'm recovering from surgery/illness and have trouble maintaining a nutritious diet.",
        "I need to gain weight for health reasons but struggle to do so in a healthy way.",
        "I get overwhelmed by conflicting dietary advice and don't know what to eat.",
        "I have difficulty chewing/swallowing certain foods.",
        "I have a sensory processing disorder that makes it hard to eat certain textures or types of food.",
        "I'm transitioning from a highly processed diet to a whole foods diet and finding it difficult.",
        "I travel frequently for work and struggle to maintain a healthy diet on the road.",
        "I have trouble eating the right portions when I cook at home.",
        "I experience food fatigue and get bored eating the same healthy foods repeatedly.",
        "I have a history of trauma related to food and eating.",
        "I need to maintain a specific diet for athletic performance and struggle to balance it with daily life.",
        "I have trouble drinking enough water throughout the day.",
        "I get acid reflux/heartburn with many foods and find it hard to eat a balanced diet.",
        "I have a fast metabolism and struggle to maintain my weight.",
        "I don't eat enough sugar - what are some healthy ways to incorporate more sugar into my diet?",
        "I have trouble eating enough for breakfast.",
        "I struggle to reach my daily calorie goal.",
    ]

    test_dataset = []
    for struggle in struggles:
        test_dataset.append({'struggle': struggle, 'text_type': 'reflection'})
        test_dataset.append({'struggle': struggle, 'text_type': 'comfort'})
        test_dataset.append({'struggle': struggle, 'text_type': 'reframing'})
        test_dataset.append({'struggle': struggle, 'text_type': 'suggestion'})
    
    with torch.inference_mode():
        # generate responses for some unseen examples
        with open(f'{args.model_id}_outputs_all-refs_unseen.txt', 'w') as f:
            
            for example in test_dataset:

                # struggle
                struggle = example['struggle']
                print('struggle:', struggle)
                f.write('struggle: ' + struggle + '\n')
                
                # old_input_ids = old_tokenizer(format_instruction_old(example), return_tensors="pt", truncation=True).input_ids[:, :-1].cuda()
                new_input_ids = new_tokenizer(format_instruction_new(example), return_tensors="pt", truncation=True).input_ids[:, :-1].cuda()
                
                # old_output_ids = old_model.generate(old_input_ids,
                #                                     max_new_tokens=100,
                #                                     pad_token_id=old_tokenizer.eos_token_id,
                # )
                new_output_ids = new_model.generate(new_input_ids,
                                                    max_new_tokens=100,
                                                    pad_token_id=new_tokenizer.eos_token_id,
                )

                # old_prediction = old_tokenizer.decode(old_output_ids[0], skip_special_tokens=True)[len(format_instruction_old(example)):]#[len(struggle):]#
                # print(f'{example["text_type"]} (one):', old_prediction.strip())
                # f.write(f'{example["text_type"]} (one): ' + old_prediction.strip() + '\n')
                
                new_prediction = new_tokenizer.decode(new_output_ids[0], skip_special_tokens=True)[len(format_instruction_new(example)):]#[len(struggle):]#
                print(f'{example["text_type"]} (all):', new_prediction.strip())
                f.write(f'{example["text_type"]} (all): ' + new_prediction.strip() + '\n')
                                
                print()
                f.write('\n')
                    

if __name__ == "__main__":
    args = ap.parse_args([] if "__file__" not in globals() else None)
    main(args)
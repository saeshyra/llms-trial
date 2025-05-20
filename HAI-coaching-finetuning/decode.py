import argparse
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
import evaluate
from sacrebleu.metrics import BLEU

from hai_coaching_dataset import HAICoachingDataset, HAICoachingDataLoaderT5, SPECIAL_TOKENS, TASK_PREFIXES
from datasets import Dataset

ap = argparse.ArgumentParser(description='Decode finetuned models on HAI-Coaching test set')
ap.add_argument('--model-id', default='google/gemma-7b-it', type=str, help='HuggingFace model to evaluate finetuned outputs of')

DEVICE = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')


def main(args: argparse.Namespace):

    # finetuned_model_dir = f"{args.model_id}_finetuned_hai-coaching"
    finetuned_model_dir = args.model_id
    
    # train_dataset = HAICoachingDataset('train')
    # train_loader = HAICoachingDataLoaderT5(train_dataset, args.model_id, batch_size=8, collate=True)

    model = AutoModelForCausalLM.from_pretrained(finetuned_model_dir)
    # model = AutoModelForSeq2SeqLM.from_pretrained(finetuned_model_dir)
    model.to(DEVICE)
    tokenizer = AutoTokenizer.from_pretrained(finetuned_model_dir)#args.model_id)#
    tokenizer.add_special_tokens(
        {"additional_special_tokens": SPECIAL_TOKENS})
    tokenizer.pad_token = tokenizer.eos_token
    # tokenizer.save_pretrained(finetuned_model_dir)
    model.resize_token_embeddings(len(tokenizer))
    # model.resize_token_embeddings(len(train_loader.tokenizer))
    
    model.load_state_dict(torch.load(f"{args.model_id}_finetuned_hai-coaching_best"))
    model.to(DEVICE)
    model.eval()

    test_dataset = HAICoachingDataset('test')
    def test_gen():
        for example in test_dataset:
            yield example
    test_dataset = Dataset.from_generator(test_gen)
    
#     def format_train_instruction(sample):
#         return f"""
# You are an expert dietitian. Below is a struggle your client is experiencing. {TASK_PREFIXES['V2'][sample['text_type']]}

# ### Struggle:
# {sample['struggle']}

# ### {sample['text_type'][0].upper()+sample['text_type'][1:]}:
# {sample['texts'][0]}
# """
    
#     def format_test_instruction(sample):
#         return f"""
# You are an expert dietitian. Below is a struggle your client is experiencing. {TASK_PREFIXES['V2'][sample['text_type']]}

# ### Struggle:
# {sample['struggle']}

# ### {sample['text_type'][0].upper()+sample['text_type'][1:]}:
# """
    # def format_test_instruction(sample):
    #     return f"""You are an expert dietitian. Below is a struggle your client is experiencing. {TASK_PREFIXES['V2'][sample['text_type']]}\n\nStruggle:"""

    def format_train_instruction(sample):
        return f"""f"<|struggle|>{sample['struggle']}<|{sample['text_type']}|>{sample['texts'][0]}<|endoftext|>"""
    def format_test_instruction(sample):
        return f"""f"<|struggle|>{sample['struggle']}<|{sample['text_type']}|>"""
    
#     def format_test_instruction(sample):
#         return f"""    
# {TASK_PREFIXES['V1'][sample['text_type']]}

# ### Struggle:
# {sample['struggle']}

# ### {sample['text_type'][0].upper()+sample['text_type'][1:]}:
# """
    
    class StoppingCriteriaSub(StoppingCriteria):
        def __init__(self, tokens=[], encounters=1):
            super().__init__()
            self.tokens = [token.to(DEVICE) for token in tokens]
            self.encounters = encounters
        def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
            for token in self.tokens:
                token_count = (token == input_ids[0]).sum().item()
                if token_count >= self.encounters:
                    return True
            return False
        
    # define stopping criteria to stop at end of text token
    stopping_criteria = StoppingCriteriaList([StoppingCriteriaSub([torch.tensor([tokenizer('<|endoftext|>').input_ids[0]])])])
    
    bleurt_scorer = evaluate.load('bleurt', module_type='metric')
    print('scores initalised, processing test dataset...')
    bleurt_scores = []
    
    with torch.inference_mode():
        # generate responses for the number of test examples specified
        with open(f'{args.model_id}_outputs.txt', 'w') as f:
            references = []
            predictions = []
            nlls = []
            
            for i, example in enumerate(test_dataset):

                # struggle
                struggle = example['struggle']
                
                # true response
                reference = example['texts']
                references.append(reference)
                
                # input_ids = tokenizer(format_test_instruction(example), return_tensors="pt", truncation=True).input_ids[:, :-1].cuda()
                # target_ids = tokenizer(f'{example["text_type"][0].upper()+example["text_type"][1:]}:\n{reference[0]}', return_tensors="pt", truncation=True).input_ids[:, :-1].cuda()
                # target_ids = tokenizer(reference[0], return_tensors='pt', padding=True, truncation=True).to(DEVICE).input_ids
                input_ids = tokenizer(f"<|struggle|>{struggle}<|{example['text_type']}|>", return_tensors='pt', padding=True, truncation=True).to(DEVICE).input_ids
                # target_ids = tokenizer(f"<|{example['text_type']}|>{reference[0]}", return_tensors='pt', padding=True, truncation=True).to(DEVICE).input_ids
                
                if i < 100:
                    print('struggle:', struggle)
                    f.write('struggle: ' + struggle + '\n')
                    print(example['text_type']+':', reference[0])
                    f.write(example['text_type']+': ' + reference[0] + '\n')
                    
                output_ids = model.generate(input_ids,
                                            max_new_tokens=100,
                                            pad_token_id=tokenizer.eos_token_id,
                                            # do_sample=True,
                                            # top_p=0.9,
                                            # temperature=0.6,
                                            stopping_criteria=stopping_criteria,
                )
                prediction = tokenizer.decode(output_ids[0], skip_special_tokens=True)[len(struggle):]#[len(format_test_instruction(example)):]#
                predictions.append(prediction.strip())
                
                if i < 100:
                    print('prediction:', prediction.strip())
                    f.write('prediction: ' + prediction.strip() + '\n')
                    
                    print()
                    f.write('\n')
                    
                if i > 100 and i % 50 == 0:
                    print(f"{i}/{len(test_dataset)} predictions generated")
                    break
                
                n_refs = len(reference)
                preds_n  = [prediction] * n_refs
                bleurt_scores.append(bleurt_scorer.compute(predictions=preds_n, references=reference)["scores"])
                
                input_ids = tokenizer(format_train_instruction(example), return_tensors="pt", truncation=True, max_length=256).input_ids.cuda()
                prompt_ids = tokenizer(format_test_instruction(example), truncation=True, max_length=256).input_ids
                target_ids = tokenizer(format_train_instruction(example), truncation=True, max_length=256).input_ids
                target_ids[:len(prompt_ids)] = [-100] * len(prompt_ids)
                target_ids = torch.tensor(target_ids).cuda()
                
                print(f"input: {input_ids.shape} | target: {target_ids.shape}")
                    
                with torch.no_grad():
                    outputs = model(input_ids, labels=target_ids)
                    # outputs = model(target_ids, labels=target_ids)
                    neg_log_likelihood = outputs.loss
                    print('nll:', neg_log_likelihood)
                nlls.append(neg_log_likelihood)
                
    with open(f'{args.model_id}_metrics.txt', 'w') as f:
            
        # initialise scores
        bleu = BLEU()
        # sacrebleu = evaluate.load('sacrebleu')
        # bleurt_scorer = evaluate.load('bleurt', module_type='metric')
        # print('scores initalised, processing test dataset...')
        
        # bleu with all references
        bleu_n_score = bleu.corpus_score(predictions, references)
        print(f'bleu (n): {bleu_n_score}')
        f.write(f'bleu (n): {bleu_n_score}\n')
        
        # bleu with 3 references
        # preds_n = []
        # refs_n = []
        # for pred, refs in zip(predictions, references):
        #     if len(refs) >= 3:
        #         preds_n.append(pred)
        #         refs_n.append(refs[:3])
        # bleu3_score = sacrebleu.compute(predictions=preds_n, references=refs_n[:100])
        # print(f'bleu (3): {round(bleu3_score["score"], 2)}')
        # f.write(f'bleu (3): {round(bleu3_score["score"], 2)}\n')

        # references = [reference[0] for reference in references]

        # bleu with a single reference
        # bleu1_score = sacrebleu.compute(predictions=predictions, references=references[:100])
        # print(f'bleu (1): {round(bleu1_score["score"], 2)}')
        # f.write(f'bleu (1): {round(bleu1_score["score"], 2)}\n')
        
        # bluert
        # bleurt_scores = bleurt_scorer.compute(predictions=predictions, references=references)
        # print(f'bleurt score: {round(np.mean(bleurt_scores["scores"]), 2)}')
        # f.write(f'bleurt score: {round(np.mean(bleurt_scores["scores"]), 2)}\n')
        
        # mean bleurt
        # bleurt_scores = []
        # for i, (pred, ref_list) in enumerate(zip(predictions, references)):
        #     n_refs = len(ref_list)
        #     preds_n  = [pred] * n_refs
        #     if i % 50 == 0:
        #         print(f'bleurt scores calculated for {i}/{len(test_dataset)}')
        #     bleurt_scores.append(bleurt_scorer.compute(predictions=preds_n, references=ref_list)["scores"])
        
        print(f'max mean bleurt score: {round(np.mean([max(scores) for scores in bleurt_scores]), 2)}')
        f.write(f'max mean bleurt score: {round(np.mean([max(scores) for scores in bleurt_scores]), 2)}\n')
        
        print(f'mean mean bleurt score: {round(np.mean([np.mean(scores) for scores in bleurt_scores]), 2)}')
        f.write(f'mean mean bleurt score: {round(np.mean([np.mean(scores) for scores in bleurt_scores]), 2)}\n')
        
        # perplexity
        mean_perplexity = torch.exp(torch.stack(nlls).mean())
        print(f'perplexity: {round(mean_perplexity.item(), 2)}')
        f.write(f'perplexity: {round(mean_perplexity.item(), 2)}\n')
    

if __name__ == "__main__":
    args = ap.parse_args([] if "__file__" not in globals() else None)
    main(args)
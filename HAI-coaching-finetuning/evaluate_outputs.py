import argparse
import numpy as np
from hai_coaching_dataset import HAICoachingDataset, TEXT_TYPES
from datasets import Dataset
import evaluate
from sacrebleu.metrics import BLEU

ap = argparse.ArgumentParser(description='Run diet coaching chatbot')
ap.add_argument('--model-id', default='google/gemma-7b-it', type=str, help='HuggingFace model to evaluate finetuned outputs of')

def process_output_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    references = []
    predictions = []

    curr_text = []

    for line in lines[1:-1]:

        # if line.startswith('struggle'):
        #     curr_text = curr_text[:-2]
        #     predictions.append(curr_text)

        if line.startswith(tuple(TEXT_TYPES[1:])):
            colon_pos = line.index(':')
            curr_text = line[colon_pos+2:]
            references.append(curr_text)

        elif line.startswith('prediction'):
            colon_pos = line.index(':')
            curr_text = line[colon_pos+2:]
            predictions.append(curr_text)

        else:
            continue
            # curr_text += line

    return references, predictions
    

def main(args: argparse.Namespace):
    
    # initialise scores
    bleu = BLEU()
    sacrebleu = evaluate.load('sacrebleu')
    bleurt = evaluate.load('bleurt', module_type='metric')
    perplexity = evaluate.load('perplexity', module_type='metric')
    print('scores initalised, processing test dataset...')
    
    references = []
    test_dataset = HAICoachingDataset('test')
    def test_gen():
        for example in test_dataset:
            yield example
    test_dataset = Dataset.from_generator(test_gen)
    for example in test_dataset:
        reference = example['texts']
        references.append(reference)
    print(f'test dataset processed with {len(references)} references, processing text file...')

    output_file = args.model_id + '_outputs.txt'
    _, predictions = process_output_file(output_file)
    print(f'output file processed with {len(predictions)} predictions, evaluating...')
    
    # bleu with all references
    bleu_n_score = bleu.corpus_score(predictions, references)
    print(f'bleu (n): {bleu_n_score}')
    
    # bleu with 3 references
    preds_n = []
    refs_n = []
    for pred, refs in zip(predictions, references):
        if len(refs) >= 3:
            preds_n.append(pred)
            refs_n.append(refs[:3])
    bleu3_score = sacrebleu.compute(predictions=preds_n, references=refs_n[:100])
    print(f'bleu (3): {round(bleu3_score["score"], 2)}')

    references = [reference[0] for reference in references]

    # bleu with a single reference
    bleu1_score = sacrebleu.compute(predictions=predictions, references=references[:100])
    print(f'bleu (1): {round(bleu1_score["score"], 2)}')
    
    # bluert
    bleurt_scores = bleurt.compute(predictions=predictions, references=references[:100])
    print(f'bleurt score: {round(np.mean(bleurt_scores["scores"]), 2)}')
    
    # perplexity
    # perplexity = perplexity.compute(predictions=references, model_id=args.model_id)
    # print(f'perplexity: {round(perplexity["mean_perplexity"], 2)}')

if __name__ == "__main__":
    args = ap.parse_args([] if "__file__" not in globals() else None)
    main(args)
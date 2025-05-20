import argparse
import os
import time
from random import randrange, sample, seed

import torch
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer

from hai_coaching_dataset import HAICoachingDataset, TASK_PREFIXES
from datasets import Dataset

from huggingface_hub import login
login("huggingface_hub_token")

ap = argparse.ArgumentParser(description='Finetune models on HAI-Coaching dataset')
ap.add_argument('--model-id', default='google/gemma-7b-it', type=str, help='HuggingFace model to finetune on HAI-Coaching dataset')

def main(args: argparse.Namespace):

    train_dataset, valid_dataset = HAICoachingDataset('train'), HAICoachingDataset('validation')

    def train_gen():
        for example in train_dataset:
            yield example
    def valid_gen():
        for example in valid_dataset:
            yield example

    train_dataset, valid_dataset = Dataset.from_generator(train_gen), Dataset.from_generator(valid_gen)

    print(f"Train dataset size: {len(train_dataset)}")
    print(train_dataset[randrange(len(train_dataset))])

    print(f"Valid dataset size: {len(valid_dataset)}")
    print(valid_dataset[randrange(len(valid_dataset))])

    def format_instruction(sample):
        return f"""
You are an expert dietitian. Below is a struggle your client is experiencing. {TASK_PREFIXES['V2'][sample['text_type']]}

### Struggle:
{sample['struggle']}

### {sample['text_type'][0].upper()+sample['text_type'][1:]}:
{sample['text']}
"""
#     def format_instruction(sample):
#         return f"""
# {TASK_PREFIXES['V1'][sample['text_type']]}

# ### Struggle:
# {sample['struggle']}

# ### {sample['text_type'][0].upper()+sample['text_type'][1:]}:
# {sample['text']}
# """
    print(format_instruction(train_dataset[randrange(len(train_dataset))]))
    print()

    # BitsAndBytesConfig int-4 config 
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )

    # Load model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(
    # model = AutoModelForSeq2SeqLM.from_pretrained(
        args.model_id, 
        quantization_config=bnb_config, 
        use_cache=False, 
        device_map="auto",
        attn_implementation="sdpa"
    )
    model.config.pretraining_tp = 1

    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # LoRA config based on QLoRA paper
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        # target_modules=['qkv_proj', 'o_proj', 'gate_up_proj', 'down_proj'], # phi
    )

    # Prepare model for training
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)

    args = TrainingArguments(
        output_dir=f"{args.model_id}_finetuned_hai-coaching",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        eval_accumulation_steps=4,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        learning_rate=2e-4,
        fp16=True,
        max_grad_norm=0.3,
        warmup_steps=10,
        lr_scheduler_type="linear",
        disable_tqdm=False,
        report_to="none",
        logging_steps=50,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        load_best_model_at_end=True,
        save_total_limit=2,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        peft_config=peft_config,
        max_seq_length=2048,
        tokenizer=tokenizer,
        packing=True,
        formatting_func=format_instruction, 
        args=args,
    )

    torch.cuda.empty_cache()

    # train
    trainer.train()#resume_from_checkpoint=True)

    # save model
    trainer.save_model()
    
if __name__ == "__main__":
    args = ap.parse_args([] if "__file__" not in globals() else None)
    main(args)
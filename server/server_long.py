#!/usr/bin/env python
# coding: utf-8

import os
import io
import sys
import json
import time
import boto3
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import transformers
from transformers import (
    AutoModel, 
    BertTokenizer, 
    BertForSequenceClassification,
    AdamW,
    LongformerTokenizerFast,
    LongformerModel, 
    LongformerConfig
)
import requests
from flask import Flask, request, Response

class ArticlesDataset(torch.utils.data.Dataset):
    def __init__(self, df, col, target_cols, tokenizer, max_len):
        self.df = df
        self.max_len = max_len
        self.text = df[col]
        self.tokenizer = tokenizer
        self.targets = df[target_cols].values
        
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, index):
        text = self.text[index]
        inputs = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            return_attention_mask=True,
            truncation=True,
            return_tensors='pt'
        )
        ids = inputs['input_ids']
        attention_mask = inputs['attention_mask']
        global_attention_mask = [
            [1 if token_id == self.tokenizer.cls_token_id else 0 for token_id in input_ids]
            for input_ids in inputs['input_ids']
        ]
        return {
            'ids': ids[0], 
            'attention_mask': attention_mask[0],
            'global_attention_mask': torch.tensor(global_attention_mask, dtype=torch.long)[0],
            'targets': torch.tensor(self.targets[index], dtype=torch.float)
        }

class LongformerArticlesLabeling(torch.nn.Module):
    def __init__(self, model_name, target_cols):
        super(LongformerArticlesLabeling, self).__init__()
        self.longformer = AutoModel.from_pretrained(model_name)
        self.fc = torch.nn.Linear(768, len(target_cols))
        
    def forward(self, input_ids=None, attention_mask=None, 
                global_attention_mask=None, 
                token_type_ids=None, position_ids=None, 
                inputs_embeds=None):
        if global_attention_mask is None:
            global_attention_mask = torch.zeros_like(input_ids)
            global_attention_mask[:, 0] = 1
        _, features = self.longformer(
            input_ids=input_ids,
            attention_mask = attention_mask,
            global_attention_mask = global_attention_mask,
            token_type_ids = token_type_ids,
            position_ids = position_ids,
            return_dict=False
        )
        output = self.fc(features)
        return output

class ArticlesPredictor():
    def __init__(self, model_name, target_cols, max_seq_len, s3,
                 device, batch_size, num_workers, model_files):
        self.tokenizer = LongformerTokenizerFast.from_pretrained(model_name)
        self.max_seq_len = max_seq_len
        self.target_cols = target_cols
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.device = device
        self.models = []
        for m_name in model_files:
            m = LongformerArticlesLabeling(
                model_name=model_name, 
                target_cols=target_cols
            )
            m.to(device)
            get_object_response = s3.get_object(
                Bucket=CREDS['name'], 
                Key=m_name
            )
            checkpoint = torch.load(
                io.BytesIO(get_object_response['Body'].read()),
                map_location=torch.device('cpu')
            )
            m.load_state_dict(checkpoint['model_state_dict'])
            m.eval()
            self.models.append(m)
            print('loaded:', m_name)
    
    def infer(self, df):
        print('PREDICT:', df.shape)
        pred_dataset = ArticlesDataset(
            df=df, 
            col='text',
            tokenizer=self.tokenizer, 
            max_len=self.max_seq_len, 
            target_cols=self.target_cols
        )
        pred_loader = torch.utils.data.DataLoader(
            pred_dataset, 
            batch_size=self.batch_size, 
            num_workers=self.num_workers, 
            shuffle=False, 
            pin_memory=True
        )
        y_pred = []
        for j, model in enumerate(self.models):
            y_pred_tmp = []
            for i, batch in enumerate(pred_loader, start=1):
                print(f'model {j}, prediction step {i}/{len(pred_loader)}   ', end='\r')
                with torch.no_grad():
                    ids = batch['ids'].to(self.device, dtype=torch.long)
                    mask = batch['attention_mask'].to(self.device, dtype=torch.long)
                    outputs = model(ids, mask)
                    y_pred_tmp.extend(torch.sigmoid(outputs).cpu().detach().numpy().tolist())
            y_pred.append(y_pred_tmp)
        y_pred = np.mean(y_pred, axis=0)
        df_pred = pd.DataFrame(y_pred) 
        df_pred.columns = [c + '_pred' for c in self.target_cols]
        return df_pred

def read_json(file_path):
    with open(file_path) as file:
        access_data = json.load(file)
    return access_data

def resp(code, data):
    return Response(status=code, mimetype='application/json', response=json.dumps(data))

def theme_validate_label():
    errors = []
    jsn = request.get_json()
    if jsn is None:
        errors.append('no JSON sent, check Content-Type header')
        return (None, errors)
    for field_name in ['text']:
        if type(jsn.get(field_name)) is not str:
            errors.append('field {} is missing or is not a string'.format(field_name))
    return (jsn, errors)

CREDS = read_json(file_path='configs/access_bucket.json')
SESSION = boto3.session.Session()
S3 = SESSION.client(
    service_name='s3',
    aws_access_key_id=CREDS['aws_access_key_id'],
    aws_secret_access_key=CREDS['aws_secret_access_key'],
    endpoint_url=CREDS['endpoint_url'] 
)
APP_CONFIG = read_json(file_path='configs/config.json')
PORT = APP_CONFIG['port_long']
CONFIG = json.load(
    S3.get_object(
        Bucket=CREDS['name'], 
        Key=f'{APP_CONFIG["model_long"]}/config.json'
    )['Body']
)
MODEL_FILES = json.load(
    S3.get_object(
        Bucket=CREDS['name'], 
        Key=f'{APP_CONFIG["model_long"]}/model_files.json'
    )['Body']
)
MODEL_FILES = [
    f'{APP_CONFIG["model_long"]}/{x.split("/")[-1]}'
    for x in MODEL_FILES
]
PREDICTOR = ArticlesPredictor(
    model_name=CONFIG['bbone'], 
    target_cols=CONFIG['target_cols'], 
    max_seq_len=CONFIG['max_seq_len'],
    s3=S3,
    device='cpu', 
    batch_size=1, 
    num_workers=1, 
    model_files=MODEL_FILES
)
LOG_PATH = 'logs'
if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
fh = logging.FileHandler(f'{LOG_PATH}/server_long.log')
LOGGER.addHandler(fh)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
fh.setFormatter(formatter)

app = Flask(__name__)

@app.route('/label', methods=['POST'])
def model_label():
    start_time = time.time()
    (jsn, errors) = theme_validate_label()
    if errors:
        return resp(400, {'errors': errors})
    d = {'text': [jsn['text']]}
    d.update(dict(zip(CONFIG['target_cols'], [0] * len(CONFIG['target_cols']))))
    df_pred = PREDICTOR.infer(pd.DataFrame(d))
    preds = {}
    for k, v in df_pred.to_dict().items():
        lbl = k.replace('_pred', '')
        preds[lbl] = v[0]
    data = {}
    data['legend'] = CONFIG['targets_description']
    data['predictions'] = preds
    msg = 'version {} - {} words, {} symbols - {} seconds'.format(
        APP_CONFIG['model'],
        len(jsn['text'].split()),
        len(jsn['text']),
        int(time.time() - start_time)
    )
    LOGGER.info(msg)
    return resp(200, {'data' : data})

@app.route('/model', methods=['GET'])
def model_config():
    return resp(200, {'data' : CONFIG})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True, use_reloader=False)

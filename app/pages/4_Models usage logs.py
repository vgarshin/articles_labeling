#!/usr/bin/env python
# coding: utf-8

import os
import json
import requests
import pandas as pd
import streamlit as st
from io import StringIO

def read_json(file_path):
    with open(file_path) as file:
        access_data = json.load(file)
    return access_data

APP_CONFIG = read_json(file_path='configs/config.json')
MODELS = [
    APP_CONFIG['model'],
    APP_CONFIG['model_long'],
    APP_CONFIG['model_xlong']
]
PORTS = [
    APP_CONFIG['port'],
    APP_CONFIG['port_long'],
    APP_CONFIG['port_xlong']
]
MPS = {k: v for k, v in zip(MODELS, PORTS)}
IP = APP_CONFIG['ip']
HEADER = {'Content-type': 'application/json'}

st.set_page_config(
    page_title='Статистика использования', 
    page_icon=':gear:'
)
st.sidebar.header(f'Логи моделей')
st.header('Статистика использования AI-моделей выявления ЦУР', divider='rainbow')

model = st.selectbox(
    'Выберите модель',
    MODELS
)
st.divider()

r = requests.get(
    'http://{}:{}/logs'.format(IP, MPS[model]),
    headers=HEADER,
    verify=True
)
logs = r.json()['data']

st.write('\n'.join(logs))
st.divider()

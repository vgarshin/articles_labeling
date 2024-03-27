import os
import json
import requests
import pandas as pd
import streamlit as st

def read_json(file_path):
    with open(file_path) as file:
        access_data = json.load(file)
    return access_data

APP_CONFIG = read_json(file_path='configs/config.json')
PORT = APP_CONFIG['port']
IP = APP_CONFIG['ip']
URL_SERVER_1 = 'http://{}:{}/model'.format(IP, PORT)
URL_SERVER_2 = 'http://{}:{}/label'.format(IP, PORT)
HEADER = {'Content-type': 'application/json'}

st.header('AI-модель выявления ЦУР', divider='rainbow')
st.subheader('Классификация научных статей для определения Целей в области устойчивого развития (ЦУР) в тексте')
st.divider()

r = requests.get(
    URL_SERVER_1,
    headers=HEADER,
    verify=True
)
model_info = r.json()['data']
st.write('Версия модели:', APP_CONFIG['model'])
st.write('Основа модели:', model_info['bbone'])
st.write('Количество ЦУР в модели:', str(len(model_info['target_cols'])))
st.divider()

text = st.text_area('Введите аннотацию (не более 500 символов)', '')
if text:
    data = {'text': text} 
    r = requests.post(
        URL_SERVER_2,
        data=json.dumps(data),
        headers=HEADER,
        verify=True
    )
    preds = r.json()['data']
    preds = [(preds['legend'][k], round(v * 100)) for k, v in preds['predictions'].items()]
    df = pd.DataFrame(
        preds,
        columns=['target', 'score']
    )
    df = df.set_index('target')
    st.divider()
    st.write('Вероятность упоминания ЦУР в статье, %')
    st.bar_chart(df)
#!/usr/bin/env python
# coding: utf-8

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

r = requests.get(
    URL_SERVER_1,
    headers=HEADER,
    verify=True
)
model_info = r.json()['data']
target_names = ', '.join([
    v for k, v in model_info['targets_description'].items()
    if 'отсутствуют' not in v
])

st.set_page_config(
    page_title='Анализ по аннотации', 
    page_icon=':bar_chart:'
)
st.sidebar.header('Анализ по аннотации')
st.header('AI-модель выявления ЦУР по аннотациям', divider='rainbow')
st.markdown(
    f"""
    Используемая в этом разделе LLM модель обучена на 1000+ 
    размеченных статей. При обучении использовались аннотации
    к научным статьям, поэтому для выявления ЦУР следует загружать 
    в форму ниже текст аннотации длиной не более 
    {model_info['max_seq_len']} слов.
    """
)
st.divider()
st.markdown(
    f"""
    #### Данные о модели
    **Версия модели:** {APP_CONFIG['model']}\n
    **Основа модели:** {model_info['bbone']}\n
    **ЦУР в модели:** {target_names}
    """
)
st.divider()

st.write('#### Введите аннотацию')
text = st.text_area('Скопируйте текст в область ниже (не более 500 слов)', '')
if text:
    with st.spinner('Подождите, модель внимательно изучает текст...'):
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
            columns=['ЦУР', 'вероятность']
        )
        df = df.set_index('ЦУР')
        st.divider()
        st.subheader('Результат оценки текста на предмет наличия ЦУР')
        for idx, row in df[df['вероятность'] > 50].iterrows():
            st.metric(
                label=idx, 
                value=f'{row["вероятность"]}%'
            )    
        st.divider()
        st.write('Вероятность упоминания ЦУР в статье, %')
        st.bar_chart(df)
    st.success('Анализ завершен')

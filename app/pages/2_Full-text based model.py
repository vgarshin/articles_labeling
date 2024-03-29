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
PORT = APP_CONFIG['port_long']
IP = APP_CONFIG['ip']
URL_SERVER_1 = 'http://{}:{}/model'.format(IP, PORT)
URL_SERVER_2 = 'http://{}:{}/label'.format(IP, PORT)
HEADER = {'Content-type': 'application/json'}

st.set_page_config(
    page_title='Анализ по тексту', 
    page_icon=':microscope:'
)

st.sidebar.header('Анализ по тексту')
st.header('AI-модель выявления ЦУР по тексту статьи', divider='rainbow')

st.markdown(
    """
    Используемая в этом разделе LLM модель обучена на 1000+ 
    размеченных статей. При обучении использовались тексты 
    научных статей, поэтому для выявления ЦУР следует загружать 
    в форму ниже текст статьи в виде файла объемом не более 4000 слов.
    """
)
st.divider()

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
st.markdown(
    f"""
    #### Данные о модели
    **Версия модели:** {APP_CONFIG['model_long']}\n
    **Основа модели:** {model_info['bbone']}\n
    **ЦУР в модели:** {target_names}
    """
)
st.divider()

st.write('#### Загрузите текст статьи')
uploaded_file = st.file_uploader('Выберите файл (в формате TXT)')
if uploaded_file is not None:
    file_name = uploaded_file.name
    if '.txt' in file_name:
        with st.spinner('Подождите, модель внимательно изучает текст...'):
            bytes_data = uploaded_file.read()
            stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
            data = {'text': stringio.read()} 
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
    else:
        st.error('Ошибка чтения файла', icon='⚠️')



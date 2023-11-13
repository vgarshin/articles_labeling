#!/usr/bin/env python
# coding: utf-8

import os
import re
import sys
import json
import boto3
import socket
from random import randint, uniform
from urllib.request import (
    Request, 
    urlopen, 
    URLError, 
    HTTPError, 
    ProxyHandler, 
    build_opener, 
    install_opener)
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from time import sleep, gmtime, strftime
from tqdm import tqdm

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 YaBrowser/19.6.1.153 Yowser/2.5 Safari/537.36'
MIN_TIME_SLEEP = .5
MAX_TIME_SLEEP = 10
MAX_COUNTS = 10
TIMEOUT = 5

class TextCollector():
    def __init__(self, user_agent, timeout, max_counts, 
                 min_time_sleep, max_time_sleep, 
                 s3_access_file, base_url,
                 proxies=None, file_content=False):
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_counts = max_counts
        self.min_time_sleep = min_time_sleep
        self.max_time_sleep = max_time_sleep
        self.proxies = proxies
        self.file_content = file_content
        opts = FirefoxOptions()
        opts.add_argument('--headless')
        self.browser = webdriver.Firefox(options=opts)
        self.s3 = boto3.client('s3')
        with open(s3_access_file) as file:
            self.access_data = json.load(file)
        self.session = boto3.session.Session()
        self.s3 = self.session.client(
            service_name='s3',
            aws_access_key_id=self.access_data['aws_access_key_id'],
            aws_secret_access_key=self.access_data['aws_secret_access_key'],
            endpoint_url='http://storage.yandexcloud.net'
        )
        self.bucket = self.access_data['bucket']
        self.base_url = base_url
    
    def search_words(self, file_path):
        with open(file_path) as file:
            lines = [line.rstrip() for line in file]
        return lines
    
    def urls_collect(self, lines):
        urls = []
        for lc, line in enumerate(lines):
            search_words = [x.strip() for x in line.split(',')]
            search = ' '.join(search_words)
            print(lc, 'search words:', search_words)
            url = f'https://{self.base_url}.ru/search?q={quote(search)}'
            self.browser.get(url)
            pages = self.browser.find_elements(
                By.XPATH, 
                '//*[@id="body"]/div[3]/div/div[1]/ul/li[*]'
            )
            sleep(uniform(self.min_time_sleep, self.max_time_sleep))
            for page in range(1, len(pages) + 1):
                print('page', page, end=' ')
                url = f'https://{self.base_url}.ru/search?q={quote(search)}&page={page}'
                self.browser.get(url)
                articles = self.browser.find_elements(
                    By.XPATH, 
                    '//*[@id="search-results"]/li[*]/h2/a'
                )
                for a in articles:
                    urls.append(a.get_attribute('href'))
                print('done')
                sleep(uniform(self.min_time_sleep, self.max_time_sleep))
        print('urls collected:', len(urls))
        urls = list(set(urls))
        print('unique urls:', len(urls))
        return urls
    
    def parce_content(self, url_page):
        counts = 0
        content = None
        while counts < self.max_counts:
            try:
                request = Request(url_page)
                request.add_header('User-Agent', self.user_agent)
                if self.proxies:
                    proxy_support = ProxyHandler(proxies)
                    opener = build_opener(proxy_support)
                    install_opener(opener)
                    context = ssl._create_unverified_context()
                    response = urlopen(
                        request, 
                        context=context, 
                        timeout=self.timeout
                    )
                else:
                    response = urlopen(request, timeout=self.timeout)
                if self.file_content:
                    content = response.read()
                else:
                    try:
                        content = response.read().decode(
                            response.headers.get_content_charset()
                        )
                    except:
                        content = None
                break
            except URLError as e:
                counts += 1
                print('URLError | ', url_page, ' | ', e, ' | counts: ', counts)
                sleep(uniform(
                    counts * self.min_time_sleep, counts * self.max_time_sleep
                ))
            except HTTPError as e:
                counts += 1
                print('HTTPError | ', url_page, ' | ', e, ' | counts: ', counts)
                sleep(uniform(
                    counts * self.min_time_sleep, counts * self.max_time_sleep
                ))
            except socket.timeout as e:
                counts += 1
                print('socket timeout | ', url_page, ' | ', e, ' | counts: ', counts)
                sleep(uniform(
                    counts * self.min_time_sleep, counts * self.max_time_sleep
                ))
        return content
    
    def text_collect(self, url):
        html = self.parce_content(url)
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('meta', property="og:title")["content"]
        citation_keywords = soup.find('meta', {'name': 'citation_keywords'})['content']
        anno = soup.find('meta', property="og:description")["content"]
        authors = ', '.join(
            [x['content'] for x in soup.find_all('meta', {'name': 'citation_author'})]
        )
        publication_date = soup.find('meta', {'name': 'citation_publication_date'})['content']
        citation_journals = ', '.join(
            [x['content'] for x in soup.find_all('meta', {'name': 'citation_journal_title'})]
        )
        citation_keywords =soup.find('meta', {'name': 'citation_keywords'})['content']
        full_text = soup.find('div', class_='ocr').text
        data = {
            "data": {
                "title": title,
                "authors": authors,
                "publication_date": publication_date,
                "citation_journals": citation_journals,
                "keywords": citation_keywords,
                "anno": anno,
                "url": url,
                "text": full_text
            }
        }
        return data
    
    def s3_write(self, data, file_path, local=False):
        try:
            if local:
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(data, file, ensure_ascii=False)
            else:
                self.s3.put_object(
                     Body=json.dumps(data, ensure_ascii=False, indent=4),
                     Bucket=self.bucket,
                     Key=file_path
                )
            return True
        except Exception as e:
            return e
    
    def s3_write_many(self, urls, prefix, start_num, len_count=5, local=False):
        try:
            for i, url in enumerate(tqdm(urls)):
                data = self.text_collect(url)
                num_str = '0' * (len_count - len(str(start_num + i))) + str(start_num + i)
                file_path = f'{prefix}_{num_str}.json'
                self.s3_write(data, file_path)
                sleep(uniform(self.min_time_sleep, self.max_time_sleep))
            return True
        except Exception as e:
            return e

def main():
    """
    Main process function. Takes sys.args to control load and process data in a form:
      python <script_name> <base_url> <prefix> <start_num>

        :script_name: name of this script `parce_texts.py`
        :search_file: file name with words to search
        :base_url: name of the site to parce
        :prefix: prefix for files to be saved into s3 bucket
        :start_num: number to be inserted to start file name
        
     example: python parce_texts.py cyberleninka search.txt sgd_article 7
    
    """
    base_url = sys.argv[1]
    search_file = sys.argv[2]
    prefix = sys.argv[3]
    start_num = int(sys.argv[4])
    
    collector = TextCollector(
        user_agent=USER_AGENT, 
        timeout=TIMEOUT, 
        max_counts=MAX_COUNTS,
        min_time_sleep=MIN_TIME_SLEEP, 
        max_time_sleep=MAX_TIME_SLEEP,
        s3_access_file='access_s3_labeling.json',
        base_url = base_url,
        proxies=None, 
        file_content=False
    )
    lines = collector.search_words(search_file)
    urls = collector.urls_collect(lines)
    result = collector.s3_write_many(
        urls,
        prefix=prefix, 
        start_num=start_num
    )
    print(result)
    print('finished')

if __name__ == '__main__':
    main()

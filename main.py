import logging
import re
import time

import requests
import schedule
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BOT_TOKEN = '7300169380:AAHWP_GtcdyIinW-6QbEJbFjNYvK2VOwRT0'  # токен бота
BOT_USER_ID = 257319019  # айди юзера

CHUNKS_CHECK_INTERVAL = 15  # в минутах
SIZE_CHANGE_CHECK_INTERVAL = 6  # в часах

MAX_CHUNKS_DIFF = 2
MAX_SIZE_CHANGE = 500

CHUNKS_MESSAGE = """
🚨Внимание, пропущено 2 чанка! Produced: {produced}, Expected: {expected}🚨
"""

SIZE_CHANGE_MESSAGE = """
❗️Внимание, изменился размер 🥩: {size_change}
"""

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


def parse_chunks():
    driver.get('https://nearscope.net/validator/snoopfear.poolv1.near/tab/dashboard')

    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'MuiBox-root.css-1uf64be')))

    chunk_block = driver.find_element(By.XPATH, '//div[contains(text(), \'Chunks:\')]')
    if not chunk_block:
        raise AssertionError

    while True:
        produced_expected = chunk_block.find_elements(By.CLASS_NAME, 'MuiBox-root.css-11lyyvk')
        if not produced_expected:
            continue

        match = re.search(r'(\d+) produced / (\d+) expected', produced_expected[0].text.strip())
        if match:
            produced = int(match.group(1))
            expected = int(match.group(2))

            logging.info(f'Данные получены! produced: {produced}, expected: {expected}')
            return produced, expected


def parse_size_change():
    driver.get('https://nearscope.net/validator/snoopfear.poolv1.near/tab/dashboard')

    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'css-fu3zz3')))

    size_change_block = driver.find_element(By.CLASS_NAME, 'MuiTypography-subtitle1')
    size_change = int(size_change_block.text.replace(',', ''))

    logging.info(f'Данные получены! size_change: {size_change}')
    return size_change


def check_chunks():
    produced, expected = parse_chunks()
    if expected - produced >= MAX_CHUNKS_DIFF:
        send_message(BOT_USER_ID, CHUNKS_MESSAGE.format(produced=produced, expected=expected))


def check_size_change():
    size_change = parse_size_change()
    if abs(size_change) >= MAX_SIZE_CHANGE:
        send_message(BOT_USER_ID, SIZE_CHANGE_MESSAGE.format(size_change=size_change))


def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    json = {
        'chat_id': chat_id,
        'text': text
    }

    response = requests.post(url, json=json)
    response.raise_for_status()

    logging.info('Оповещение отправлено!')


logging.basicConfig(level=logging.INFO)

schedule.every(CHUNKS_CHECK_INTERVAL).minutes.do(check_chunks)
schedule.every(SIZE_CHANGE_CHECK_INTERVAL).hours.do(check_size_change)

schedule.run_all()

while True:
    schedule.run_pending()
    time.sleep(1)

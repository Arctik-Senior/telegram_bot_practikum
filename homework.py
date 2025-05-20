import os
import sys
import logging
import requests
from json.decoder import JSONDecodeError

from dotenv import load_dotenv
import time

import telegram

from core import (
    LoadEnvException,
)

load_dotenv()
PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

required_vars = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID',
]

RETRY_PERIOD = 600  # 600 seconds or 10 minutes
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger("main")

stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setLevel(logging.INFO)

logger.addHandler(stream_handler)


def check_tokens():
    """
    Get env variables.
    If cant find var then `raise exception` and `send message`.
    """
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        raise ValueError(
            f'Не хватает обязательных переменных:'
            f'{', '.join(missing_vars)}'
        )


def send_message(bot, message):
    """
    Send message in Telegram, and duplicate message in logs (debug).
    Get token and chat id from env.
    """
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение отправлено {message}')
    except Exception as e:
        logger.debug(f'Сообщение не отправилось {e}')


def get_api_answer(timestamp):
    """Get homework status by Yandex Practicum API."""
    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        return error

    code = response.status_code

    if code != 200:
        raise requests.RequestException(f"response code:{code}")

    try:
        return response.json()
    except JSONDecodeError as error:
        return error


def check_response(response):
    """Validation of the response."""
    if not isinstance(response, dict):
        raise TypeError('Не правильный тип данных.')

    homework = response.get('homeworks')

    if not isinstance(homework, list):
        raise TypeError('Неправильный тип данных.')

    if not isinstance(homework[0], dict):
        raise TypeError('Не правильный тип данных.')

    homework = homework[0]

    if not homework:
        return None

    logger.info('Успешное подтвержение ответа')
    return homework


def parse_status(homework) -> str:
    """Get and return status of a homework."""
    homework_name = homework.get('homework_name')
    status_hm = homework.get('status')

    if not (homework_name or status_hm):
        raise ValueError('Нету имени домашки или статуса')

    verdict = HOMEWORK_VERDICTS.get(status_hm)

    if not verdict:
        raise ValueError('Некоректный статус.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main function what contains program logic."""
    global logger
    last_status = ''
    last_api_error = None

    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        encoding='UTF-8'
    )

    load_env_error_msg = check_tokens()

    bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))
    timestamp = int(time.time()) - 3_000_000

    if load_env_error_msg:
        send_message(bot, str(load_env_error_msg))
        raise LoadEnvException

    while True:
        try:
            response = get_api_answer(timestamp)

            if isinstance(response, Exception):
                logger.error(response.text)
                if response != last_api_error:
                    send_message(bot, response.text)
                last_api_error = response
                continue

            last_api_error = None
            homework = check_response(response)

            if homework:
                status = parse_status(homework)

                if status != last_status:
                    send_message(bot, status)
                    logger.info(status)

                else:
                    logger.error('Статуса нет.')
        except Exception as error:
            message = f'программа не работает {error}'
            send_message(bot, message)
            logger.error(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()

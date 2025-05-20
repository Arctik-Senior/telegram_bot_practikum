import os
import sys
import logging
from helpers import check_tokens, send_message, get_api_answer, check_response, parse_status # noqa E501

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

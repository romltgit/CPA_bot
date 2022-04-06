import telebot
from binance.client import Client
from settings import *
from db_models import *

# Инициализация Телеграм-бота
bot = telebot.TeleBot(settings['telegram_token'])

# Инициализация клиента Binance-api
client = Client(settings['binance_keys']['api_key'], settings['binance_keys']['secret_key'])

# Создание таблицы Alerts в БД, если её нет
db.create_tables([Alert])

# Отпарвка сообщений об ошибках пользователю
def send_error(chat_id,error):
    bot.send_message(chat_id, errors[error], parse_mode="Markdown")
import telebot
from binance.client import Client
from settings import *
from db_models import *
import json
import os.path
import time
import logging

# Логирование
logfile = 'errors.log'
log = logging.getLogger("my_log")
log.setLevel(logging.ERROR)
FH = logging.FileHandler(logfile, encoding='utf-8')
basic_formater = logging.Formatter('%(asctime)s : [%(levelname)s] : %(message)s')
FH.setFormatter(basic_formater)
log.addHandler(FH)

# Инициализация Телеграм-бота
bot = telebot.TeleBot(settings['telegram_token'])

# Инициализация клиента Binance-api
client = Client(settings['binance_keys']['api_key'], settings['binance_keys']['secret_key'])

# Создание таблицы Alerts в БД, если её нет
db.create_tables([Alert])

# Отпарвка сообщений об ошибках пользователю
def send_error(chat_id,error):
    bot.send_message(chat_id, errors[error], parse_mode="Markdown")

# Проверка валидности и наличия тикера в списке тикеров биржи 
def ticker_is_confirmed(ticker,tickers_list):
    if( (ticker.count('/') == 1 and ticker.replace('/','') in tickers_list['spot']) or (ticker.count('/') == 0 and ticker in tickers_list['futures']) ):
        return True
    else:
        return False

# Загрузка в JSON списка уникальных тикеров
def get_tickers():
    tikers = {
        "futures":[],   # Фьючерские тикеры
        "spot":[]       # Спот тикеры
    }

    try: 
        #Получение фьючерсных тикеров

        ticker = []
        info = client.futures_exchange_info()   # USDT-futures
        for j in info['symbols']:
            ticker.append(j['pair'])
        info = client.futures_coin_exchange_info()  # COIN-futures
        for j in info['symbols']:
            ticker.append(j['pair'])
        tikers["futures"] = list(set(ticker))

        #Получение спотовых тикеров
        ticker = []
        info = client.get_all_tickers()        # SPOT
        for j in info:
            ticker.append(j['symbol'])
        tikers["spot"] = list(set(ticker))

        # Запись в JSON 
        with open("tickers_list.json", "w") as write_file:
            json.dump(tikers, write_file,indent=4)
        return tikers
    except:
        log.error("Ошибка при обновлении тикеров")

# Загрузка тикеров из JSON
def get_tickers_from_json():
    tickers_list = []
    while(tickers_list == []):
        try:
            if(os.path.exists("tickers_list.json")):
                with open("tickers_list.json", "r") as read_file:
                    tickers_list = json.load(read_file)
                    return tickers_list
            else:
                return get_tickers()    # Если файла нет, получает тикеры и добавляет в файл
        except:
            log.error("Не удалось считать JSON")
            time.sleep(0.1)

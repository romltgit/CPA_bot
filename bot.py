import telebot
from binance.client import Client
from settings import *
import json
from db_models import *

# Инициализация Телеграм-бота
bot = telebot.TeleBot(settings['telegram_token'])

# Инициализация клиента BInance-api
client = Client(settings['binance_keys']['api_key'], settings['binance_keys']['secret_key'])

# Создание таблицы Alerts в БД, если её нет
db.create_tables([Alert])


# Обновление и запись в JSON уникальных тикеров Binance
def tickers_update():
    tikers = []
    info = client.futures_exchange_info()
    for j in info['symbols']:
        tikers.append(j['pair'])
    info = client.futures_coin_exchange_info()
    for j in info['symbols']:
        tikers.append(j['pair'])
    info = client.get_all_tickers()
    for j in info:
        tikers.append(j['symbol'])
    tikers = list(set(tikers))
    with open("tickers_list.json", "w") as write_file:
        json.dump(tikers, write_file)

# Отправка сообщения об ошибке
def send_error(chat_id,error):
    bot.send_message(chat_id, errors[error], parse_mode="Markdown")



tickers_update()
# Загрузка из JSON списка уникальных тикеров
with open("tickers_list.json", "r") as read_file:
    tickers_list = json.load(read_file)

# Телеграм-Бот
@bot.message_handler(content_types=['text'])

def help(message):
    lst = message.text.split()
    match lst[0]:
        case "/help":
            # Описание команды /help
            bot.send_message(message.chat.id, commands_description['help'], parse_mode="Markdown")

        case "/start":
            # Описание команды start
            bot.send_message(message.chat.id, commands_description['start'],parse_mode="Markdown")

        case "/add":
            # Добавление нового уведомления

            # Получение из БД всех активных уведомлений пользователя
            results = Alert.select().where(Alert.chat_id == message.chat.id)    

            # Проверка на превышение лимита кол-ва уведомлений и тикеров
            if(len(results) <= settings['user_alerts_limit'] and len(set([j.ticker for j in results])) <= settings['user_tickers_limit']): 

                if(len(lst) >= 3):      # Проверка валидности команды: Команда должна быть больше 3 слов (комментарий к уведомлению необязателен)
                    ticker = str(lst[1]).upper()        # Тикер, который указал пользователь

                    if((ticker.replace('/','')) in tickers_list):       # Проверка наличия тикера в списке тикеров биржи 
                                                                        # (удаление '/' необходимо, т.к биржа выдает все тикеры без разделителей)
                        try:
                            price = float(lst[2])       # Цена активации уведомления

                            if(price > 0):
                                text = ''                   
                                for j in lst[3:len(lst)]:
                                    text = text + j + " "
                                text = text[:-1]        # Комментарий к уведомлению

                                # Добавление уведомления в БД
                                query = Alert.insert({'chat_id':message.chat.id,'ticker':ticker,'price':price,'comment':text}).execute()

                                bot.send_message(message.chat.id, "Уведомление *%s* по цене *%s* добавлено с комментарием: *%s*" %(ticker,price,text),parse_mode="Markdown")
                            else: 
                                send_error(message.chat.id, 'invalid_price')   # Невалидная цена уведомления 
                        except:
                            send_error(message.chat.id, 'invalid_command') # Невалидная цена уведомления (не Float)

                    else: send_error(message.chat.id, 'invalid_ticker')    # Тикер отсутвует на бирже 

                else: send_error(message.chat.id, 'invalid_command')   # Невалидный синтаксис команды

            else: send_error(message.chat.id, 'limit')  # Превышение лимита кол-ва уведомлений и тикеров

        case "/remove":
            # Удаление уведомления(й) пользователя

            # Проверка валидности команды:
            if(len(lst) <= 3 and len(lst) > 1):
                if(lst[1] == "all"):
                    # Удаление всех активных уведомлений и отправка сообщения пользователю

                    query = Alert.delete().where(Alert.chat_id == message.chat.id ).execute()
                    bot.send_message(message.chat.id, "Все уведомления удалены", parse_mode="Markdown")

                else:
                    ticker = str(lst[1]).upper()        # Тикер, который указал пользователь
                    if((ticker.replace('/','')) in tickers_list):       # Проверка наличия тикера в списке тикеров биржи 
                        if(len(lst) == 2):
                            # Удаление всех активных уведомлений по тикеру и отправка сообщения пользователю
                            
                            query = Alert.delete().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker).execute()
                            bot.send_message(message.chat.id, "Все уведомления тикера %s удалены" %(ticker), parse_mode="Markdown")
                        else:
                            # Удаление конкретного уведомления

                            try:
                                price = float(lst[2])
                                results = Alert.select().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker and Alert.price == price)

                                # Проверка наличия этого уведомления
                                if(len(results) != 0):
                                    # Удаление уведомления и отправка сообщения пользователю

                                    query = Alert.delete().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker and Alert.price == price).execute()
                                    bot.send_message(message.chat.id, "Уведомление тикера *%s* при цене *%s* удалено" %(ticker,price), parse_mode="Markdown")
                                else:
                                    send_error(message.chat.id, 'no_alerts_for_ticker_and_price')  # Нет конретного уведомления
                            except:
                                send_error(message.chat.id, 'invalid_command') # Невалидная цена уведомления (не Float)

                    else: send_error(message.chat.id, 'invalid_ticker')    # Тикер отсутвует на бирже
                        
            else: send_error(message.chat.id, 'invalid_command')   # Невалидный синтаксис команды


        case "/show":
            # Вывод активных уведомлений пользователя

            if(len(lst) == 2):
                text = ''
                ticker = str(lst[1]).upper()    # Тикер, который указал пользователь

                if(lst[1] == "all"):    
                    # Вывод всех активных уведомлений у пользователя

                    results = Alert.select().where(Alert.chat_id == message.chat.id)
                    for alert in results:
                        text = "%s \n\nТикер: %s \nЦена: %s\nКомментарий: %s" %(text,alert.ticker,alert.price,alert.comment)
                    
                    if(text != ''): 
                        text = "Активные уведомления:" + text
                        bot.send_message(message.chat.id, text ,parse_mode="Markdown")
                    else:
                        send_error(message.chat.id, 'no_alerts')   # Нет уведомлений


                elif(ticker.replace('/','') in tickers_list):
                    # Вывод всех активных уведомлений конкретного тикера у пользователя

                    results = Alert.select().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker)
                    for alert in results:
                        text = "%s \n\nТикер: %s \nЦена: %s\nКомментарий: %s" %(text,alert.ticker,alert.price,alert.comment)
                    if(text != ''): 
                        text = "Активные уведомления для тикера %s: %s" %(ticker,text)
                        bot.send_message(message.chat.id, text ,parse_mode="Markdown")
                    else:
                        send_error(message.chat.id, 'no_alerts_for_ticker') # Нет уведомлений для конкретного тикера

                else: send_error(message.chat.id, 'invalid_ticker') # Тикер отсутвует на бирже

            else: send_error(message.chat.id, 'invalid_command') # Невалидный синтаксис команды
        case _:
            send_error(message.chat.id, 'unknown_command')  # Неизвестная команда 

bot.polling(none_stop=True, interval=0)
from settings import *
from db_models import *
from clients_and_defs import *
import threading

global_tickers = {}

# Получение всех тикеров биржи, разделеных по категориям
def tickers_update():
    global global_tickers
    global_tickers = get_tickers()
    time.sleep(5)

# Проверка активации уведомлений
def get_bar(ticker):
    global global_tickers   #Список тикеров
    now_time = (int(time.time()) // 60 - 1)*60*1000     #Начало текущей минуты
    info = []
    if('/' in ticker):      # Определение спот или фьючерсный тикер
        if(ticker.replace('/','') in global_tickers["spot"]):   # Проверка, есть ли тикер в списке тикеров (спот).
                                                                # Она необходима, т.к Binance иногда делистит тикеры (особенно спот), а в БД запись остается
            try: 
                info = client.get_historical_klines(ticker.replace('/',''),"1m",now_time)   # Получение последней минутной свечи 
                                                                                            # (из-за пинга и задержек самого Binance, иногда может придти 2 свечи)
            except:
                log.error("Ошибка при получении данных тикера %s (Binance Spot)" %(ticker))     # Логирование ошибок
        else:
            # Если тикер не найден

            # Отправить сообщение всем пользователям, у которых есть активное уведомление на этот тикер
            query = Alert.select().where(Alert.ticker == ticker)
            users = list({j.chat_id for j in query})
            for user in users:
                bot.send_message(user, "Тикер *%s* больше недоступен для отслеживания. Все уведомления на этот тикер удалены" %(ticker),parse_mode="Markdown")

            # Удалить из БД все уведомления на неподдерживаемый тикер
            query = Alert.delete().where(Alert.ticker == ticker).execute()
            return
    else:
        if(ticker in global_tickers["futures"]):       # Проверка, есть ли тикер в списке тикеров (фьючерсы).
            try: 
                info = client.futures_historical_klines(ticker,"1m",now_time)   # Получение последней минутной свечи 
                
            except:
                log.error("Ошибка при получении данных тикера %s (Binance Futures)" %(ticker))      # Логирование ошибок
        else:
            # Если тикер не найден

            # Отправить сообщение всем пользователям, у которых есть активное уведомление на этот тикер
            query = Alert.select().where(Alert.ticker == ticker)
            users = list({j.chat_id for j in query})
            for user in users:
                bot.send_message(user, "Тикер *%s* больше недоступен для отслеживания. Все уведомления на этот тикер удалены" %(ticker),parse_mode="Markdown")

            # Удалить из БД все уведомления на неподдерживаемый тикер
            query = Alert.delete().where(Alert.ticker == ticker).execute()
            return
    if(info != []):
        high = max([float(info[-1][2]),float(info[-2][2])])   #Хай последних 2х минутных свечей
        low = min([float(info[-1][3]),float(info[-2][3])])    #Лой последних 2х минутных свечей
        # Получение всех уведомлений на этом тикере
        results = Alert.select().where(Alert.ticker == ticker)

        # Проверка уведомлений
        for alert in results:
            if(alert.price <=high and alert.price >=low):   #Если цена уведомления есть в текущей свече
                    #отправка сообщений пользователю и удаление уведомления из бд
                    bot.send_message(alert.chat_id, "*%s* достиг цены *%s*\n\nКомментарий: *%s*" %(ticker,alert.price,alert.comment),parse_mode="Markdown")
                    query = Alert.delete().where(Alert.id == alert.id).execute()



def start_alert_bot():
    global global_tickers
    # Обновляем список тиикеров при старте
    tickers_update()

    # Создаем поток, обновляющий список тикеров каждые 5 сек
    update_tickers_thread = threading.Thread(target=tickers_update)
    update_tickers_thread.start()

    connection = True       # Логирование подключения
    while(True):
        try:
            status = client.get_system_status()     # Проверка статуса Binance 
            connection = True
        except:
            if(connection):
                log.error("Нет подключения к Binance")
                connection = False
            continue

        if(not(status["status"])):            # Проверка статуса и соеденения status: (0: normal，1：system maintenance)
            # Пересоздаем поток после его исполнения
            if(not(update_tickers_thread.is_alive())):
                update_tickers_thread = threading.Thread(target=tickers_update)
                update_tickers_thread.start()

            # Получаем список всех уведомлений из БД
            results = Alert.select()
            # Список уникальных тикеров
            tickers_list = list({j.ticker for j in results})

            # Если есть уведомления
            if(tickers_list != []):
                threads = []
                for ticker in tickers_list:
                    # Превышение лимита (12) потоков
                    # Из-за ограничения Binance на кол-ва запросов в секунду максимум может быть только 10 потоков для запроса данных, 1 поток основной, 1 поток получает тикеры
                    while(threading.active_count() >= 12):
                        time.sleep(0.05)

                    # На каждую монету создаем поток функции get_bar
                    t = threading.Thread(target=get_bar, args=(ticker,))
                    threads.append(t)
                    t.start()
                # Ждем завершения работы всех потоков этой итерации
                for t in threads:
                    t.join()



# Запуск бота, управляющего уведомлениями
alert_thread = threading.Thread(target=start_alert_bot)
alert_thread.start()


# Телеграм-Бот
@bot.message_handler(content_types=['text'])
def help(message):
    lst = message.text.split()
    match lst[0]:
        case "/help":
            # Описание команды /help
            bot.send_message(message.chat.id, commands_description['help'], parse_mode="Markdown")

        case "/start":
            # Описание команды /start
            bot.send_message(message.chat.id, commands_description['start'],parse_mode="Markdown")

        case "/add":
            # Добавление нового уведомления

            # Получение из БД всех активных уведомлений пользователя
            results = Alert.select().where(Alert.chat_id == message.chat.id) 
            # Проверка на превышение лимита кол-ва уведомлений и тикеров
            if(len(results) <= settings['user_alerts_limit'] and len(set([j.ticker for j in results])) <= settings['user_tickers_limit']): 

                if(len(lst) >= 3):      # Проверка валидности команды: Команда должна быть больше 3 слов (комментарий к уведомлению необязателен)
                    ticker = str(lst[1]).upper()                    # Тикер, который указал пользователь
                    tickers_list = get_tickers_from_json()          # Получаем список тикеров биржи

                    if(ticker_is_confirmed(ticker,tickers_list)):       # Проверка валидности и наличия тикера в списке тикеров биржи 
                        try:
                            price = float(lst[2])       # Цена активации уведомления

                            if(price > 0 and price < 10000000):
                                text = ''                   
                                for j in lst[3:len(lst)]:
                                    text = "%s%s " %(text,j)
                                
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

                    results = Alert.select().where(Alert.chat_id == message.chat.id)
                    if(len(results) != 0):
                        query = Alert.delete().where(Alert.chat_id == message.chat.id).execute()
                        bot.send_message(message.chat.id, "Все уведомления удалены", parse_mode="Markdown")
                    else:
                        send_error(message.chat.id, 'no_alerts') 

                else:
                    ticker = str(lst[1]).upper()        # Тикер, который указал пользователь
                    if(len(lst) == 2):
                        # Удаление всех активных уведомлений по тикеру и отправка сообщения пользователю
                        results = Alert.select().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker)
                        if(len(results) != 0):
                            query = Alert.delete().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker).execute()
                            bot.send_message(message.chat.id, "Все уведомления тикера %s удалены" %(ticker), parse_mode="Markdown")
                        else:
                            send_error(message.chat.id, 'no_alerts_for_ticker') 
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

                else:
                    # Вывод всех активных уведомлений конкретного тикера у пользователя
                    results = Alert.select().where(Alert.chat_id == message.chat.id and Alert.ticker == ticker)
                    for alert in results:
                        text = "%s \n\nТикер: %s \nЦена: %s\nКомментарий: %s" %(text,alert.ticker,alert.price,alert.comment)
                    if(text != ''): 
                        text = "Активные уведомления для тикера %s: %s" %(ticker,text)
                        bot.send_message(message.chat.id, text ,parse_mode="Markdown")
                    else:
                        send_error(message.chat.id, 'no_alerts_for_ticker') # Нет уведомлений для конкретного тикера


            else: send_error(message.chat.id, 'invalid_command') # Невалидный синтаксис команды
        case _:
            send_error(message.chat.id, 'unknown_command')  # Неизвестная команда 

bot.polling(none_stop=True, interval=0)

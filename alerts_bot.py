import time
import threading
from clients_and_defs import *

global_tickers = {} # Тикеры биржи

# Получение всех тикеров биржи, разделеных по категориям
def tickers_update():
    global global_tickers
    global_tickers = get_tickers()
    time.sleep(5)

# Проверка активации уведомлений
def get_bar(ticker):
    global global_tickers   #Список тикеров

    
    now_time = (int(time.time()) // 60)*60*1000     #Начало текущей минуты
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
        high = float(info[-1][2])   #Хай последней минутной свечи
        low = float(info[-1][3])    #Лой последней минутной свечи
        # Получение всех уведомлений на этом тикере
        results = Alert.select().where(Alert.ticker == ticker)

        # Проверка уведомлений
        for alert in results:
            if(alert.price <=high and alert.price >=low):   #Если цена уведомления есть в текущей свече
                    #отправка сообщений пользователю и удаление уведомления из бд
                    bot.send_message(alert.chat_id, "*%s* достиг цены *%s*\n\nКомментарий: *%s*" %(ticker,alert.price,alert.comment),parse_mode="Markdown")
                    query = Alert.delete().where(Alert.id == alert.id).execute()


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
        print('ok')
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

    
    
            
from settings import *
from db_models import *
from clients_and_defs import *

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
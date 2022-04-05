from peewee import *
db = SqliteDatabase('db/alert.db')

class Alert(Model):
    chat_id = IntegerField()
    ticker = TextField()
    price = FloatField()
    comment = TextField()
    class Meta:
        database = db  # модель будет использовать базу данных 'people.db'
        db_table = 'Alerts'
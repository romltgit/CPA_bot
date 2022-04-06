from peewee import *
db = SqliteDatabase('db/alert.db')

class Alert(Model):
    id = PrimaryKeyField(unique=True)
    chat_id = IntegerField()
    ticker = TextField()
    price = FloatField()
    comment = TextField()
    class Meta:
        database = db
        db_table = 'Alerts'
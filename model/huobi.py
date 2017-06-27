#encoding=utf-8

from pony.orm import *
from db import db
from datetime import datetime

class HuobiTradeHistory(db.Entity):
    price = Required(float)
    trade_time = Required(datetime)
    amount = Required(float)
    direction = Required(str)
    tradeId = PrimaryKey(int, size=64)
    type_ = Required(str)
    en_type = Required(str)



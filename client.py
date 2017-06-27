#encoding=utf-8

import sys

import time
from datetime import datetime
import requests
import ConfigParser
from model.huobi import *

"""
    将时间戳转换为日期字符串,时间戳为精确到秒的整数
"""
def revert_to_str(timestamp, delimiter='-'):
    _t = time.localtime(timestamp)
    str_t = time.strftime("%Y{}%m{}%d %H:%M:%S".format(delimiter, delimiter), _t)
    return str_t

"""
    将时间戳转为datetime
"""
def revert_to_date(timestamp, delimiter='-'):
    str_t = revert_to_str(timestamp, delimiter)
    date_t = datetime.strptime(str_t, "%Y{}%m{}%d %H:%M:%S".format(delimiter, delimiter))
    return date_t

class Trade(object):
    def __init__(self):
        pass

    @db_session
    def get_market(self):
        detail_url = "http://api.huobi.com/staticmarket/detail_ltc_json.js"
        result = requests.get(detail_url)
        result = result.json()
        p_new = result["p_new"]
        for trade in result["trades"]:
            price = trade["price"]
            t = trade["ts"]
            trade_time = revert_to_date(t/1000.0)
            type_ = trade["type"]
            en_type = trade["en_type"]
            tradeId = trade["tradeId"]
            direction = trade["direction"]
            amount = trade["amount"]
            _trade = get(trade for trade in HuobiTradeHistory if trade.tradeId == tradeId)
            if not _trade:
                _trade = HuobiTradeHistory(tradeId=tradeId, type_=type_, trade_time=trade_time, price=price, en_type=en_type, direction=direction, amount=amount)
        commit()
        level_url = "http://api.huobi.com/staticmarket/depth_ltc_150.js"
        result = requests.get(level_url)
        result = result.json()
        sells_sum_trade = 0
        buy_sum_trade = 0
        for sell in result["asks"]:
            sells_sum_trade += sell[1]
        for buy in result["bids"]:
            buy_sum_trade += buy[1]
        data = {}
        data["new"] = p_new
        data["sells_sum_trade"] = sells_sum_trade
        data["buy_sum_trade"] = buy_sum_trade
        print("buy_sum_trade:", buy_sum_trade)
        print("sell_sum_trade", sells_sum_trade)
        proportion_trade = buy_sum_trade / (buy_sum_trade + sells_sum_trade)
        print("proportion_trade:", proportion_trade)
        return data

    #计算最近time_gap秒之内的买盘和卖盘总量，预测趋势
    @db_session
    def trend(self, new_price, time_gap=600):
        t = time.time() - time_gap
        date_t = revert_to_date(t)
        trades = select(trade for trade in HuobiTradeHistory if trade.trade_time > date_t)
        sell_sum_money = 0
        sell_sum_trade = 0
        buy_sum_money = 0
        buy_sum_trade = 0
        for trade in trades:
            if trade.direction == "sell":
                sell_sum_money += trade.price * trade.amount
                sell_sum_trade += trade.amount
            else:
                buy_sum_money += trade.price * trade.amount
                buy_sum_trade += trade.amount
        sell_avg_price = 0.0
        buy_avg_price = 0.0
        proportion_trade = 0.0
        try:
            sell_avg_price = sell_sum_money / sell_sum_trade
            buy_avg_price = buy_sum_money / buy_sum_trade
            #已成交的单子中买盘所占的比例 越接近于1表示有大量单子进入
            proportion_trade =  buy_sum_trade / (sell_sum_trade + buy_sum_trade)
        except ZeroDivisionError, e:
            print("ignore zero!")
        print("Now Price:", new_price)
        print("Buy Avg Price:", buy_avg_price, "Buy Sum :", buy_sum_trade)
        print("Sell Avg Price:", sell_avg_price, "Sell Sum :", sell_sum_trade)
        print("Proportion for Trade ;buy_num/sell_num", proportion_trade)
#        print trades

    def run(self):
        while True:
            data = self.get_market()
            new_price = data["new"]
            self.trend(new_price, time_gap=60)
            time.sleep(2)

def main():
    if len(sys.argv) < 2:
        print("conf file need! ")
        exit(0)
    config = sys.argv[1]
    conf = ConfigParser.ConfigParser()
    conf.read(config)
    m_host = conf.get("mysql", "m_host")
    m_user = conf.get("mysql", "m_user")
    m_passwd = conf.get("mysql", "m_passwd")
    m_db = conf.get("mysql", "m_db")
    db.bind("mysql", host=m_host, user=m_user, passwd=m_passwd, db=m_db)
    db.generate_mapping(create_tables=True)
    trade = Trade()
    trade.run()

if __name__ == "__main__":
    main()

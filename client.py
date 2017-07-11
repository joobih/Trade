#encoding=utf-8

import sys

import time
from datetime import datetime
import requests
import ConfigParser
from model.huobi import *

import logging

logger = logging.getLogger("mylog")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(name)-12s %(asctime)s %(levelname) -8s %(message)s")
file_handler = logging.FileHandler("test.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

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

"""
    将日期字符串转换为datetime
"""
def revertstr_to_date(str_t, delimiter='-'):
    date_t = datetime.strptime(str_t, "%Y{}%m{}%d%H%M%S".format(delimiter, delimiter))
    return date_t

"""
    获取列表中的最大值和最小值
"""
def get_most_price(trades):
    max_price = 0
    min_price = 1 << 31
    for trade in trades:
        if trade[2] > max_price:
            max_price = trade[2]
        if trade[3] < min_price:
            min_price = trade[3]
    print max_price,min_price
    return max_price, min_price

class Trade(object):
    def __init__(self):
        pass

    #获取实时成交数据，实时价格等
    #获取150条买盘卖盘深度数据(当前托盘或者压盘的趋势)
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
        sell_more_trades_list_100 = []
        buy_more_trades_list_100 = []
        sell_more_trades_list_500 = []
        buy_more_trades_list_500 = []
        sell_more_trades_list_1000 = []
        buy_more_trades_list_1000 = []
        #累计卖单中的最大单量
        sell_max_account = 0
        #累计卖单中的最大单量的价格
        sell_max_price = 0
        #累计买单中的最大单量
        buy_max_account = 0
        #累计买单中的最大单量的价格
        buy_max_price = 0
        for sell in result["asks"]:
            if sell[1] > sell_max_account:
                sell_max_trade = sell[1]
                sell_max_price = sell[0]
            if sell[1] >= 100:
                sell_more_trades_list_100.append(sell)
            if sell[1] >= 500:
                sell_more_trades_list_500.append(sell)
            if sell[1] >= 1000:
                sell_more_trades_list_1000.append(sell)
            sells_sum_trade += sell[1]
        for buy in result["bids"]:
            if buy[1] >= 100:
                buy_more_trades_list_100.append(buy)
            if buy[1] >= 500:
                buy_more_trades_list_500.append(buy)
            if buy[1] >= 1000:
                buy_more_trades_list_1000.append(buy)
            buy_sum_trade += buy[1]
        sell_more_trades_list_100.sort(lambda x,y: cmp(y[0], x[0]))
        buy_more_trades_list_100.sort(lambda x,y: cmp(y[0], x[0]))
        sell_more_trades_list_500.sort(lambda x,y: cmp(y[0], x[0]))
        buy_more_trades_list_500.sort(lambda x,y: cmp(y[0], x[0]))
        sell_more_trades_list_1000.sort(lambda x,y: cmp(y[0], x[0]))
        buy_more_trades_list_1000.sort(lambda x,y: cmp(y[0], x[0]))
        logger.error("Sell more trades list(卖单里面数量大于100的单子):{}".format(sell_more_trades_list_100))
        logger.error("Buy more trades list(买单里面数量大于100的单子):{}".format(buy_more_trades_list_100))
        logger.error("Sell more trades list(卖单里面数量大于500的单子):{}".format(sell_more_trades_list_500))
        logger.error("Buy more trades list(买单里面数量大于500的单子):{}".format(buy_more_trades_list_500))
        logger.error("Sell more trades list(卖单里面数量大于1000的单子):{}".format(sell_more_trades_list_1000))
        logger.error("Buy more trades list(买单里面数量大于1000的单子):{}".format(buy_more_trades_list_1000))
        data = {}
        data["new"] = p_new
        data["sells_sum_trade"] = sells_sum_trade
        data["buy_sum_trade"] = buy_sum_trade
        logger.error("buy_sum_trade:{}".format(buy_sum_trade))
        logger.error("sell_sum_trade:{}".format(sells_sum_trade))
        proportion_trade = buy_sum_trade / (buy_sum_trade + sells_sum_trade)
        data["proportion_trade"] = proportion_trade
        #如果proportion_trade < 0.3 说明卖盘有大单打压，价格不好上去。
        logger.error("proportion_trade:{}".format(proportion_trade))
        return data

    #计算最近time_gap秒之内的已经成交的买盘和卖盘总量，预测趋势
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
            #已成交的单子中买盘所占的比例 越接近于1表示有大量单子进入，价格也将上升
            proportion_trade =  buy_sum_trade / (sell_sum_trade + buy_sum_trade)
        except ZeroDivisionError, e:
            print("ignore zero!")
        logger.error("Now Price:{}".format(new_price))
        logger.error("Buy Avg Price:{};Buy Sum:{}".format(buy_avg_price, buy_sum_trade))
        logger.error("Sell Avg Price:{};Sell Sum:{}".format(sell_avg_price, sell_sum_trade))
        logger.error("Proportion for Trade ;buy_num/sell_num:{}".format(proportion_trade))
#        print trades

    @db_session
    def KDJ(self):
        url = "http://api.huobi.com/staticmarket/ltc_kline_001_json.js"
        result = requests.get(url)
        trades = result.json()
        trades.sort(lambda x,y: cmp(x[0], y[0]))
        #将存在于数据库中的最大一条的kdj数据查询出来
        newest_trade_time = db.select("select max(trade_time) from huobikdj where trade_time < (select max(trade_time) from huobikdj)")
        print newest_trade_time
        if newest_trade_time[0]:
            newest_trade_time = newest_trade_time[0]
            newest_kdj = get(k for k in HuobiKDJ if k.trade_time == newest_trade_time)
            K,D = newest_kdj.K, newest_kdj.D
        else:
            K, D = 50, 50
            newest_trade_time = datetime(1990,1,1)
        for i,trade in enumerate(trades):
            trade[0] = trade[0][0:-3]
            trade[0] = revertstr_to_date(trade[0], delimiter="")
            if trade[0] <= newest_trade_time:
                continue
            Cn = trade[4]
            #获取9个单位（单位可以表示为1分钟，5分钟，15分钟，日，周，月等）内的最大值和最小值
            if i < 9:
                Hn, Ln = get_most_price(trades[:i+1])
            else:
                Hn, Ln = get_most_price(trades[i-9:i+1])
            if (Hn - Ln) == 0:
                K = 50
                D = 50
            else:
                RSV = ((Cn - Ln) / (Hn - Ln)) * 100
                K = (RSV + 2*K) / 3.0
                D = (K + 2*D) / 3.0
            trade.append(K)
            trade.append(D)
            trade.append(K-D)
            if (K < 10 and D < 20) or (K > 80 and D > 80):
                print trade[0],trade[4],trade[6],trade[7],trade[8], K, D
            else:
                print trade[0],trade[4],trade[6],trade[7],trade[8]
            huobi_kdj = get(h for h in HuobiKDJ if h.trade_time == trade[0])
            if not huobi_kdj:
                HuobiKDJ(trade_time=trade[0], price=trade[4], K=K, D=D)
            else:
                huobi_kdj.price = trade[4]
                huobi_kdj.K = K
                huobi_kdj.D = D
            commit()

    def run(self):
        while True:
#            data = self.get_market()
#            new_price = data["new"]
#            self.trend(new_price, time_gap=60)
            self.KDJ()
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

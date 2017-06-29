#encoding=utf-8

import requests
import time

def KDJ(trades):
    trades.sort(lambda x,y: cmp(x[0], y[0]))
    K,D = 50,50
    for trade in trades:
        Cn = trade[4]
        Hn = trade[2]
        Ln = trade[3]
        if (Hn - Ln) == 0:
            K = 50
            D = 50
            print(trade, "    ")
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




url = "http://api.huobi.com/staticmarket/ltc_kline_001_json.js"
result = requests.get(url)
result = result.json()
#trades = [["20170910",123],["20170911", 23]]
KDJ(result)

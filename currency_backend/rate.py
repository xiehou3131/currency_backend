import pdb
import time
import json
import random
import pytz
import datetime
from datetime import timezone
import numpy as np

import argparse
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from currency_backend.tools import json_wrap
from .dbconfig import *

# connect influxdb
bucket_trades = "Klines"
client = InfluxDBClient(
    url="http://localhost:8086",
    token=
    "-vKh8eaHviakWO6CO7CP4AsJAcK7WF845TcCb4mHz22SsYdW0JQ6HtQJ1kwun8eoFC4ariy_SHVquwsMy3nw5Q==",
    org="NUS")
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()

def getCoinInfo(request):
    q_str = '''from (bucket: "{}") |> range(start: -15m)'''.format(
        bucket_trades)
    q_str += "|> filter(fn: (r) =>"
    coins = list(coin.find({}, {"_id": 0}))
    for i in range(len(coins)):
        if i > 0:  # 跳过USDT
            if i != len(coins) - 1:
                q_str += 'r["_measurement"] == "' + coins[i]["symbol"] + '_USDT" or '
            else:
                q_str += 'r["_measurement"] == "' + coins[i]["symbol"] + '_USDT")'

    # r["_measurement"] == "BTC_USDT" or r["_measurement"] == "ETH_USDT" or r["_measurement"] == "BNB_USDT" or r["_measurement"] == "SOL_USDT" or r["_measurement"] == "ADA_USDT" or r["_measurement"] == "XRP_USDT" or r["_measurement"] == "DOT_USDT" or r["_measurement"] == "DOGE_USDT" or r["_measurement"] == "AVAX_USDT" or r["_measurement"] == "SHIB_USDT")'''
    q_str += '''|> filter(fn: (r) => r["_field"] == "high" or r["_field"] == "low" or r["_field"] == "volume")'''
    q_str += '''|> last()'''
    q_str += '''|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'''
    prices = {}
    try:
        tables = query_api.query(q_str)

        for table in tables:
            for row in table.records:  # 每次可以查到6条数据，是6种不同的平台报的价格，这里要取一个加权平均
                p = float(row.values["high"] + row.values["low"]) / 2
                q = float(row.values["volume"])
                if row.values["_measurement"].replace("_USDT", "") in prices.keys():
                    P += p * q
                    Q += q
                else:
                    P = p * q
                    Q = q
                if Q != 0:
                    prices[row.values["_measurement"].replace("_USDT", "")] = P / Q
                else:
                    prices[row.values["_measurement"].replace("_USDT", "")] = 0
                # prices[row.values["_measurement"]] = row.values[""]

        prices["USDT"] = 1.0
        data = {"prices": prices, "time": row.values["_time"],"coins":coins}

    except Exception as e:
        data = {"prices": {"USDT":1.0}, "time": time_now(), "coins": coins}
        print(e)
    return json_wrap({"status":200,"data":data},no_log=True)

if __name__ == "__main__":
    get_rate()


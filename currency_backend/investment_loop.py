import copy
import random
import string

import os
import json
from functools import wraps
from .dbconfig import *
from bson import json_util
from .tools import *
import datetime
from .view import check_login, check_parameters
import random

scheme_template = {
    "id": 0,
    "username": "",
    "create_time": "",
    "start_time": "",
    "invest_cycle": 0, # 以秒为单位的timestamp
    "invest_amount": 0,
}

timestamp_zero = int(timestamp_now() / DAY) * DAY

while True:
    # sleep until the next day
    sleep_time = DAY - (timestamp_now() % DAY)
    time.sleep(sleep_time)
    timestamp_zero += DAY

    # start investment
    T = 0 # total amount of Token

    all_plans = list(plans.find())
    plans = []
    for item in all_plans:
        time_interval = timestamp_zero - item["start_time"]
        if time_interval > 0 and time_interval % item["invest_cycle"] == 0:
            # TODO: call web3 txn to tranfer the token to the hot wallet

            plans.append(item)
            T += item["invest_amount"]

    t = T * 0.999

    # 0AM + rand(0, 4)
    time_buy_0 = int(random.uniform(0, 4) * 3600) + timestamp_zero
    sleep_time_0 = time_buy_0 - timestamp_now()
    if sleep_time_0 > 0:
        time.sleep(sleep_time_0)

    # TODO: buy t/4 btc

    # 0AM + rand(4, 8)
    time_buy_1 = int(random.uniform(4, 8) * 3600) + timestamp_zero
    sleep_time_1 = time_buy_1 - timestamp_now()
    if sleep_time_1 > 0:
        time.sleep(sleep_time_1)

    # TODO: buy t/4 btc

    # 0AM + rand(8, 12)
    time_buy_2 = int(random.uniform(8, 12) * 3600) + timestamp_zero
    sleep_time_2 = time_buy_2 - timestamp_now()
    if sleep_time_2 > 0:
        time.sleep(sleep_time_2)

    # TODO: buy t/4 btc

    # 0AM + rand(12, 16)
    time_buy_3 = int(random.uniform(12, 16) * 3600) + timestamp_zero
    sleep_time_3 = time_buy_3 - timestamp_now()
    if sleep_time_3 > 0:
        time.sleep(sleep_time_3)

    # TODO: buy t/4 btc

    btc = 0 # TODO: calculate the total btc amount

    for plan in plans:
        btc_increment = (plan["invest_amount"] / T) * btc
        
        user = list(myauths.find({"username": plan["username"]}))[0]
        user["btc_amount"] += btc_increment

        myauths.save(user)



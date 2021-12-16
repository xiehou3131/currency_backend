import datetime
import json
import re
import random
import time

import pymongo
import pytz
from bson import Regex
from dateutil.relativedelta import relativedelta

from currency_backend.tools import time_now

myclient = pymongo.MongoClient('mongodb://currency:Qw123456789@localhost:27017/', connect=False)
mydb = myclient['currency']
myauths = mydb["userInfo"]
logs = mydb["logs"]
coin = mydb["coinInfo"]
test = mydb["test"]

if __name__ == '__main__':
    # date = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('Asia/Shanghai'))
    # datetime.datetime.utcnow()得到的是当前UTC的时间，如当前北京时间8点，则得到的是UTC的0点，如果用了replace，则认为这个0点是东八区的0点，那么插入到数据库中记录的UTC的时间就是前一天的16点
    date = datetime.datetime.utcnow()
    # print(date.isoformat())
    # next_day = date + datetime.timedelta(days=1) # 日期加1天
    # last_day = date + datetime.timedelta(days=-1)  # 日期减1天
    startDate = date - relativedelta(years=3) # 添加3年的数据
    startDate = date - relativedelta(days=3)  # 添加3年的数据
    # test.insert_one({"time": date, "value": random.uniform(0, 100000)})
    # print(date_format,next_day,last_day)

    # diff = next_day - last_day
    # day2 = datetime.datetime.strptime("2021-12-13 06:00:00", "%Y-%m-%d %H:%M:%S") # 时间差计算是统一按照UTC时间算的
    # diff = date - day2
    # print(diff.days)
    # print(date - endDate)
    i = 0
    dates = []
    while (date - startDate).days != -1:  # 插入数据到指定日期，比如一个月之前
        print(i, startDate, date - startDate, random.uniform(0, 100000))
        dates.append({"time": startDate, "value": 140000 + random.uniform(-10000, 10000)})
        startDate = startDate + datetime.timedelta(hours=2)
        # time.sleep(0.1)
        i += 1
    myauths.update_one({"username": "naibowang@comp.nus.edu.sg"},
                       {'$set': {"schemes.$[item].propertyLogs": dates}},
                       upsert=True,
                       array_filters=[
                           {"item.id": 1},  # 往第一套方案的properties的数组里添加该数组
                       ]
                       )  # 往第一套方案的properties的数组里添加该对象
    # frequency = 12
    # timeRange = 730
    # count = 1
    # date = datetime.datetime.utcnow()
    # if timeRange<27:
    #     startDate = date - relativedelta(days=timeRange)
    # elif timeRange <181: # 月份时间差计算
    #     startDate = date - relativedelta(months=timeRange/30)
    # else: #年份时间差计算
    #     startDate = date - relativedelta(years=timeRange / 365)
    # count = (date - startDate).days
    #
    # schemeChartLogs = list(myauths.find({"username": "naibowang@comp.nus.edu.sg"},
    #                                         {"schemes.propertyLogs": {
    #                                             "$slice": [-1*count * frequency-100, count * frequency+100] # 在原来的基础上多拿100条数据，以防万一
    #                                         }, "username": 1, "schemes.id": 1, "schemes.name": 1, "_id": 0}))[0]  # 得到用户所有方案的propertyLogs，按数量算好的
    # propertyLogs = schemeChartLogs["schemes"][0]["propertyLogs"]
    # propertyLogs.reverse()
    # outputLogs = []
    #
    # # 如果请求的时间点正好是日志记录的时间点，则会多出一条数据，即如果日志是11:12:14记录的，那么在11:12:14访问接口就会多出一条数据，因为log["time"]
    # # startDate = propertyLogs[0]["time"] -relativedelta(days=2)
    # print(startDate)
    # # t = datetime.datetime.strptime("2021-12-13 06:13:00", "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime("2021-12-12 06:13:00", "%Y-%m-%d %H:%M:%S")
    # # print(t,t.days)
    #
    # dateCursor = "" # 数据游标
    # start = False # 是否已经开始加入列表
    # for log in propertyLogs:
    #     if (log["time"] - startDate).days >=0:
    #         # if not start:
    #         #     outputLogs.append(propertyLogs[index-1])
    #         if timeRange <= 31: # 一个月之内，全部打印
    #             outputLogs.append(log)
    #         elif timeRange <400: # 超过一个月少于两年，每隔一天打印一次数据
    #             if dateCursor != log["time"].strftime("%Y-%m-%d"):
    #                 outputLogs.append(log)
    #                 dateCursor = log["time"].strftime("%Y-%m-%d")
    #         else:# 两年及以上，每3天打印一次记录
    #             if dateCursor != log["time"].strftime("%Y-%m-%d"):
    #                 dateCursor = log["time"].strftime("%Y-%m-%d")
    #                 if (log["time"] - startDate).days % 3 == 0:
    #                     outputLogs.append(log)
    #     else:
    #         if propertyLogs[0]["time"].strftime("%H:%M:%S") != date.strftime("%H:%M:%S"):
    #             outputLogs.append(log) # 把最后一条数据拿到，因为算过去24小时的变化应该有25条数据，除非当前查询时间和最后一条日志时间的时分秒完全相同
    #         break;
    #
    # outputLogs.reverse() # 时间升序排序
    #
    # print(len(outputLogs),outputLogs[0],outputLogs[-1])
    # print(outputLogs)
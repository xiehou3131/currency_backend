import random
import string

import os
from django.http import HttpResponse
import json
from functools import wraps
from .dbconfig import *
from bson import json_util
from .tools import *
from django.core.cache import cache
import datetime
from .view import check_login, check_parameters
import requests


@check_login
def getSchemeMenu(request):
    # num = list(myauths.aggregate(
    #     [{'$match': {'username': request.session["username"]}},
    #      {'$project': {'count': {"$size": '$schemes'}}}
    #      ])) # 查询scheme数组内元素的个数，即有几套方案
    menus = list(myauths.find({"username": request.session["username"]},
                              {"schemes.id": 1, "username": 1, "schemes.name": 1, "_id": 0}))  # 得到用户的方案个数
    return json_wrap({"status": 200, "data": menus[0]}, no_log=True)


@check_login
def getSchemeOverview(request):
    menus = list(myauths.find({"username": request.session["username"]},
                              {"schemes.id": 1, "username": 1, "schemes.name": 1,
                               "schemes.propertyLogs": {"$slice": [-20, 20]}, "schemes.properties": 1, "_id": 0}))
    return json_wrap({"status": 200, "data": menus[0]}, no_log=True)


@check_login
@check_parameters(["id", 'range'])
def getSchemeChart(request):
    frequency = 12  # 每天插入的日志条数
    timeRange = int(request.POST["range"])
    date = datetime.datetime.utcnow()
    if timeRange < 27:
        startDate = date - relativedelta(days=timeRange)
    elif timeRange < 181:  # 月份时间差计算
        startDate = date - relativedelta(months=timeRange / 30)
    else:  # 年份时间差计算
        startDate = date - relativedelta(years=timeRange / 365)
    count = (date - startDate).days
    schemeChartLogs = list(myauths.find({"username": request.session["username"]},
                                        {"schemes.propertyLogs": {
                                            "$slice": [-1 * count * frequency - 100, count * frequency + 100]
                                            # 在原来的基础上多拿100条数据，以防万一
                                        }, "username": 1, "schemes.id": 1, "schemes.name": 1, "_id": 0}))[
        0]  # 得到用户所有方案的propertyLogs，按数量算好的
    for scheme in schemeChartLogs['schemes']:  # 输出指定scheme的信息
        if scheme["id"] == float(request.POST['id']):
            propertyLogs = scheme["propertyLogs"]
    propertyLogs.reverse()
    outputLogs = []

    dateCursor = ""  # 数据游标
    for log in propertyLogs:
        if (log["time"] - startDate).days >= 0:
            if timeRange <= 31:  # 一个月之内，全部打印
                outputLogs.append(log)
            elif timeRange < 400:  # 超过一个月少于两年，每隔一天打印一次数据
                if dateCursor != log["time"].strftime("%Y-%m-%d"):
                    outputLogs.append(log)
                    dateCursor = log["time"].strftime("%Y-%m-%d")
            else:  # 两年及以上，每3天打印一次记录
                if dateCursor != log["time"].strftime("%Y-%m-%d"):
                    dateCursor = log["time"].strftime("%Y-%m-%d")
                    if (log["time"] - startDate).days % 3 == 0:
                        outputLogs.append(log)
        else:
            if propertyLogs[0]["time"].strftime("%H:%M:%S") != date.strftime("%H:%M:%S"):
                outputLogs.append(log)  # 把最后一条数据拿到，因为算过去24小时的变化应该有25条数据，除非当前查询时间和最后一条日志时间的时分秒完全相同
            break;

    outputLogs.reverse()  # 时间升序排序
    output = {"propertyLogs": outputLogs}
    return json_wrap({"status": 200, "data": output}, no_log=True)


@check_login
@check_parameters(["id"])
def getSchemeAccount(request):
    schemeChartLogs = list(myauths.find({"username": request.session["username"]},
                                        {"username": 1, "schemes.properties": 1,
                                         "schemes.propertyLogs": {
                                             "$slice": [-20, 20]
                                         },
                                         "schemes.id": 1, "schemes.name": 1, "_id": 0}))[
        0]  # 得到用户所有方案的propertyLogs，按数量算好的
    output = {}
    for scheme in schemeChartLogs['schemes']:  # 输出指定scheme的信息
        if scheme["id"] == float(request.GET['id']):
            output = scheme
    # 得到log最早的一条是什么时候，从而控制overview是否显示更多的时间范围标签
    propertyLogs = list(myauths.find({"username": request.session["username"]},
                                     {"username": 1,
                                      "schemes.propertyLogs": {
                                          "$slice": 1
                                      },
                                      "schemes.id": 1, "schemes.name": 1, "_id": 0}))[0]
    output["propertyStartTime"] = time_now()
    for scheme in propertyLogs['schemes']:  # 输出指定scheme的信息
        if scheme["id"] == float(request.GET['id']):
            if len(scheme["propertyLogs"]) > 0:
                output["propertyStartTime"] = scheme["propertyLogs"][0]["time"]

    return json_wrap({"status": 200, "data": output}, no_log=True)


@check_login
@check_parameters(["info", "pagination"])
def getSchemeDepositLogs(request):
    info = json.loads(request.POST["info"])
    pagination = json.loads(request.POST["pagination"])
    output = {}
    if pagination["firstInvoke"]:
        try:
            # 请求李远服务器的等待时间最多只有10秒，超出后必须返回数据，哪怕没有最新的log，注意10秒不是那边服务器的处理时间，是从发送请求到处理请求全部的等待时间，所以如果后台处理时间为1秒，则整个过程至少需要3秒
            # r = requests.get('http://currency.naibo.wang:8081/currency_backend/testDelay', timeout=10)
            time.sleep(1)
        except requests.exceptions.Timeout as e:
            output["invokeStatus"] = "timeout"
        # time.sleep(3)
    schemeChartLogs = list(myauths.find({"username": request.session["username"]},
                                        {"username": 1,
                                         "schemes.chargeLogs": 1,
                                         "schemes.id": 1, "schemes.name": 1, "_id": 0}))[0]

    for scheme in schemeChartLogs['schemes']:  # 输出指定scheme的信息
        if scheme["id"] == float(info["id"]):
            output = scheme
    output["chargeLogs"].reverse()  # 倒序排序

    if len(pagination["showCurrent"]) > 0:  # 只显示当前币种
        output["chargeLogs"] = list(filter(lambda x: x["coin"] == info["coin"], output["chargeLogs"]))
    output["rows"] = len(output["chargeLogs"])
    output["chargeLogs"] = output["chargeLogs"][
                           (pagination["currentPage"] - 1) * pagination["perPage"]:pagination["currentPage"] *
                                                                                   pagination["perPage"]]
    # print(pagination)
    return json_wrap({"status": 200, "data": output}, no_log=True)


@check_login
@check_parameters(["chain", "coin"])
def waitGetSchemeAddress(request):
    output = {}
    # print(request.POST["id"], request.POST["chain"],request.session["username"])
    query = list(myauths.find({"username": request.session["username"],
                            "schemes": {
                                "$elemMatch": {
                                    "chainAddresses.name": request.POST["chain"],  # 嵌套数组写法
                                    "id": float(request.POST["id"]),
                                }
                            }}, {"schemes.chainAddresses": 1, "username": 1, "schemes.id": 1, "_id": 0}))
    # 查询id方案中用户的chainAddresses数组中现在是否存在name为chain这个对象，不存在返回空数组
    # print(query)
    if len(query) == 0: # 如果账户已经有这个chain的address了，就不需要向后台查询了，否则向后台查询
        try:
            # r = requests.get('http://currency.naibo.wang:8081/currency_backend/testDelay', timeout=10)
            time.sleep(1)
            output["address"] = "New generated address"
        except requests.exceptions.Timeout as e:
            output["invokeStatus"] = "timeout"
            output["address"] = "Sorry, we cannot get your chain address now"
    else:
        chainAddresses = list(filter(lambda x: x["id"] == float(request.POST["id"]) , query[0]["schemes"]))[0]["chainAddresses"]
        output["address"] = list(filter(lambda x: x["name"] == request.POST["chain"] , chainAddresses))[0]["address"]

    return json_wrap({"status": 200, "data": output}, no_log=True)


@check_login
@check_parameters(["selected", 'desc'])
def addScheme(request):
    info = list(myauths.find({"username": request.session["username"]},
                             {"schemes.id": 1, "username": 1, "_id": 0}))
    new_scheme_id = 1.0
    if len(info[0]['schemes']) > 0:
        new_scheme_id = info[0]['schemes'][-1]["id"] + 1
    new_scheme_name = request.POST['selected']
    if request.POST['selected'] == "2":
        new_scheme_name = request.POST['desc']
    new_scheme = {
        "id": new_scheme_id,
        "name": new_scheme_name,
        "create_time": time_now(),
        "properties": [
            {
                "symbol": "USDT",
                "addresses": [
                    {
                        "chain": "BEP20(BSC)",
                        "amount": 0.0,
                        "update_time": time_now()
                    }
                ]
            }
        ],
        "chainAddresses": [
        ],
        "propertyLogs": [
        ],
        "chargeLogs": [
        ],
        "withdrawLogs": [
        ],
        "investPlans": {
            "update_time": time_now(),
            "contents": [
                {
                    "coin": "USDT",
                    "percentage": 100.0
                }
            ]
        }
    }
    myauths.update_one({"username": request.session['username']},
                       {'$push': {"schemes": new_scheme}},
                       upsert=False,
                       )
    return json_wrap({"status": 200, "msg": "Scheme has been successfully added!", "data": {"id": new_scheme_id}},
                     no_response=True)


@check_login
@check_parameters(["selected", 'desc', 'id'])
def editSchemeDesc(request):
    new_scheme_name = request.POST['selected']
    if request.POST['selected'] == "2":
        new_scheme_name = request.POST['desc']
    myauths.update_one({"username": request.session["username"]},
                       {'$set': {"schemes.$[item].name": new_scheme_name}},
                       upsert=True,
                       array_filters=[
                           {"item.id": float(request.POST["id"])},
                       ]
                       )  # 修改properties数据方法,如果USDT存在，则把整个数组修改成上面的值,不存在则不做任何事
    return json_wrap(
        {"status": 200, "msg": "Scheme Descrption has been successfully modified!", "data": {"id": new_scheme_name}},
        no_response=True)

if __name__ == '__main__':
    query = list(myauths.find({"username": "naibowang@comp.nus.edu.sg",
                            "schemes": {
                                "$elemMatch": {
                                    "chainAddresses.name": "BEP20 (BSC)",  # 嵌套数组写法
                                    "id": 1,
                                }
                            }}, {"schemes.chainAddresses": 1, "username": 1, "schemes.id": 1, "_id": 0}))
    print(query)
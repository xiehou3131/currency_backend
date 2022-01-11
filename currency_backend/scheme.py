import copy
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

scheme_template = {
    "id": 0,
    "name": 0,
    "create_time": "",
    "investStatus":"normal",
    "properties": [
        {
            "symbol": "USDT",
            "addresses": [
                {
                    "chain": "BEP20 (BSC)",
                    "amount": 0.0,
                    "withdrawAmount": 0.0,  # 今天已经占用的提币额度
                    "books": [],  # 记录的地址簿
                    "update_time": ""
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
    "investPlans": [{
        "create_time": "",
        "contents": [
            {
                "coin": "USDT",
                "percentage": 100.0
            }
        ]
    }]
}


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
@check_parameters(["id"])
def getInvestPlan(request):
    userSchemeData = list(myauths.find({"username": request.session["username"]},
                              {"schemes.id": 1, "username": 1, "schemes.name": 1,
                               "schemes.investPlans": {"$slice": [-1, 1]}, "_id": 0}))
    investPlan = list(filter(lambda x: x["id"] == float(request.POST["id"]), userSchemeData[0]["schemes"]))[0][
        "investPlans"][0]
    # print(investPlan)
    return json_wrap({"status": 200, "data": investPlan}, no_log=True)

@check_login
@check_parameters(["plan","rebalance","id"])
def newInvestPlan(request):
    if request.POST['rebalance'] == "false": # 如果不是rebalance
        plan = json.loads(request.POST["plan"])
        userSchemeData = list(myauths.find({"username": request.session["username"]},
                                           {"schemes.id": 1, "username": 1, "schemes.name": 1,
                                            "schemes.investStatus": 1}))
        investStatus = list(filter(lambda x: x["id"] == float(request.POST["id"]), userSchemeData[0]["schemes"]))[0][
            "investStatus"]
        if investStatus != "normal":
            return json_wrap({"status": 500,
                              "msg": "We are now processing your last invest plan, please wait until it is done."})
        totalPercentage = 0
        print(plan)
        for coinInfo in plan:
            try:
                coinInfo["percentage"] = float(coinInfo["percentage"])
                if coinInfo["percentage"] < 0 or coinInfo["percentage"] >100:
                    return json_wrap({"status": 500,
                                      "msg": "Parameter error, percentage cannot be smaller than 0 or bigger than 100!"})
                else:
                    totalPercentage += coinInfo["percentage"]
            except:
                return json_wrap({"status": 500,
                                  "msg": "Parameter error, percentage is not a float!"})
            theCoin = list(coin.find({"symbol": coinInfo["coin"]}))
            if len(theCoin) == 0:
                return json_wrap({"status": 500,
                                  "msg": "Sorry, we cannot find the specified coin %s!" % coinInfo["coin"]})
        if totalPercentage!= 100:
            return json_wrap({"status": 500,
                              "msg": "Parameter error, percentages do not add up to 100!"})

        myauths.update_one({"username": request.session['username']},
                           {'$addToSet': {"schemes.$[item].investPlans": {"create_time":time_now(),"contents":plan}
                                          },"$set":{"schemes.$[item].investStatus":"processing"}},
                           upsert=True,
                           array_filters=[
                               {"item.id": float(request.POST["id"])},
                           ]
                           )
    else: # 如果是rebalance，只需要更改个投资状态
        myauths.update_one({"username": request.session['username']},
                           {"$set": {"schemes.$[item].investStatus": "processing"}},
                           upsert=True,
                           array_filters=[
                               {"item.id": float(request.POST["id"])},
                           ]
                           )
    try:
        params = {
            "username": request.session["username"],
            "id": float(request.POST["id"]),
        }
        print(params)
        r = requests.get('http://chain.naibo.wang/updateInvestPlan',params=params,timeout=10)
        print(r.text)
    except requests.exceptions.Timeout as e:
        return json_wrap({"status": 500,
                          "msg": "Sorry, we cannot process your invest now!"})
    return json_wrap({"status": 200, "msg": "Invest Plan has been successfully submitted, please wait for our platform to adjust your account!"})

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
                                         "schemes.id": 1,"schemes.investStatus":1, "schemes.name": 1, "_id": 0}))[
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
@check_parameters(["type"])
def waitSchemeLogs(request):
    time.sleep(3)
    return json_wrap({"status": 200, "new_log": True}, no_log=True)


@check_login
@check_parameters(["params"])
def withdrawCoin(request):
    output = {"status": 200, "msg": "Withdraw request has been successfully submitted and being processed now!"}
    params = json.loads(request.POST["params"])
    params["username"] = request.session["username"]
    try:
        # 请求李远服务器的等待时间最多只有10秒，超出后必须返回数据，哪怕没有最新的log，注意10秒不是那边服务器的处理时间，是从发送请求到处理请求全部的等待时间，所以如果后台处理时间为1秒，则整个过程至少需要3秒
        params = {
            "username": params["username"],
            "id": float(params["id"]),
            "chain": params["chain"],
            "coin": params["coin"],
            "address":params["address"],
            "quantity":float(params["quantity"])
        }
        # print(params)
        # r = requests.get('http://currency.naibo.wang:8081/currency_backend/testDelay?type='+type, timeout=10)
        r = requests.post('http://chain.naibo.wang/withdraw/', data=params,timeout=15)
        # print(r.text)
        if r.text == "true":
            output["status"] = 200
            output["msg"] = "Withdraw Success!"
        else:
            output["status"] = 500
            output["msg"] = "Sorry, we cannot process your withdraw request now!"
    except requests.exceptions.Timeout as e:
        output["status"] = 500
        output["msg"] = "Sorry, we cannot process your withdraw request now!"
    return json_wrap(output)


@check_login
@check_parameters(["info", "pagination", "type"])
def getSchemeLogs(request):
    info = json.loads(request.POST["info"])
    pagination = json.loads(request.POST["pagination"])
    type = request.POST["type"]
    temp = {}
    output = {}
    # if pagination["firstInvoke"]:
    #     try:
    #         # 请求李远服务器的等待时间最多只有10秒，超出后必须返回数据，哪怕没有最新的log，注意10秒不是那边服务器的处理时间，是从发送请求到处理请求全部的等待时间，所以如果后台处理时间为1秒，则整个过程至少需要3秒
    #         # r = requests.get('http://currency.naibo.wang:8081/currency_backend/testDelay?type='+type, timeout=10)
    #         time.sleep(0)
    #     except requests.exceptions.Timeout as e:
    #         output["invokeStatus"] = "timeout"
    #     # time.sleep(3)
    if type == "deposit":
        schemeLogs = list(myauths.find({"username": request.session["username"]},
                                       {"username": 1,
                                        "schemes.chargeLogs": 1,
                                        "schemes.id": 1, "schemes.name": 1, "_id": 0}))[0]
    else:
        schemeLogs = list(myauths.find({"username": request.session["username"]},
                                       {"username": 1,
                                        "schemes.withdrawLogs": 1,
                                        "schemes.id": 1, "schemes.name": 1, "_id": 0}))[0]
    for scheme in schemeLogs['schemes']:  # 输出指定scheme的信息
        if scheme["id"] == float(info["id"]):
            temp = scheme

    if type == "deposit":
        output["logs"] = temp["chargeLogs"]
    else:
        output["logs"] = temp["withdrawLogs"]
    output["logs"].reverse()  # 倒序排序
    if len(pagination["showCurrent"]) > 0:  # 只显示当前币种
        output["logs"] = list(filter(lambda x: x["coin"] == info["coin"], output["logs"]))
    output["rows"] = len(output["logs"])
    output["logs"] = output["logs"][
                     (pagination["currentPage"] - 1) * pagination["perPage"]:pagination["currentPage"] *
                                                                             pagination["perPage"]]
    # print(pagination)
    return json_wrap({"status": 200, "data": output}, no_log=True)


@check_login
@check_parameters(["chain", "coin", "id"])
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
    if len(query) == 0:  # 如果账户已经有这个chain的address了，就不需要向后台查询了，否则向后台查询
        try:
            params={
                "username":request.session["username"],
                "id":float(request.POST["id"]),
                "chain":request.POST["chain"],
            }
            r = requests.get('http://chain.naibo.wang/getAddress', params=params,timeout=10)
            # time.sleep(1)
            output["address"] = r.text
        except requests.exceptions.Timeout as e:
            output["invokeStatus"] = "timeout"
            output["address"] = "Sorry, we cannot get your chain address now"
    else:
        chainAddresses = list(filter(lambda x: x["id"] == float(request.POST["id"]), query[0]["schemes"]))[0][
            "chainAddresses"]
        output["address"] = list(filter(lambda x: x["name"] == request.POST["chain"], chainAddresses))[0]["address"]

    return json_wrap({"status": 200, "data": output}, no_log=True)


@check_login
@check_parameters(["chain", "coin", "id", "tag", "address"])
def addAddressBook(request):
    output = {"status": 200, "msg": "Address has been successfully added!"}
    query = list(myauths.find({"username": request.session["username"],
                               "schemes": {  # 多级嵌套写法！
                                   "$elemMatch": {
                                       "properties": {
                                           "$elemMatch": {
                                               "symbol": request.POST["coin"],
                                               "addresses.chain": request.POST["chain"],
                                           }
                                       },
                                       "id": float(request.POST["id"]),
                                   }
                               }}, {"username": 1, "schemes.id": 1, "_id": 0}))
    # 查询id方案中用户的chainAddresses数组中现在是否存在name为chain这个对象，不存在返回空数组
    if len(query) == 0:  # 如果查到了这个chain的存在，则直接添加，否则查币和链存不存在,不存在返回错误，存在的话向用户数据里添加信息
        queryChain = list(coin.find({"symbol": request.POST["coin"],
                                     "supportChains": {  # 多级嵌套写法！
                                         "$elemMatch": {
                                             "name": request.POST["chain"],
                                         }
                                     }}, {"_id": 0}))
        if len(queryChain) == 0:  # 找不到post过来的币名对应的链名
            output = {"status": 500, "msg": "Sorry, we cannot find specified coin or chain info!"}
            return json_wrap(output)
        else:
            queryCoin = list(myauths.find({"username": request.session["username"],
                                           "schemes": {  # 多级嵌套写法！
                                               "$elemMatch": {
                                                   "properties.symbol": request.POST["coin"],
                                                   "id": float(request.POST["id"]),
                                               }
                                           }}, {"username": 1, "schemes.id": 1, "_id": 0}))
            if len(queryCoin) == 0:  # 如果币也不存在,添加币
                new_scheme = copy.deepcopy(scheme_template)
                new_coin = new_scheme["properties"][0]
                new_coin["symbol"] = request.POST["coin"]
                new_coin["addresses"][0]["chain"] = request.POST["chain"]
                new_coin["addresses"][0]["update_time"] = time_now()
                new_coin["addresses"][0]["books"].append({"tag": request.POST["tag"],
                                                          "address": request.POST["address"]})
                myauths.update_one({"username": request.session['username']},
                                   {'$addToSet': {"schemes.$[item].properties": new_coin
                                                  # {"symbol": request.POST["coin"], "addresses": [{
                                                  #     "chain": request.POST["chain"],
                                                  #     "amount": 0.0,
                                                  #     "update_time": time_now(),
                                                  #     "withdrawAmount": 0.0,
                                                  #     "books": []
                                                  # }]}
                                                  }},
                                   upsert=True,
                                   array_filters=[
                                       {"item.id": float(request.POST["id"])},
                                   ]
                                   )  # 用addToSet以便避免添加重复数据
            else:  # 币存在但是链不存在
                new_scheme = copy.deepcopy(scheme_template)
                new_chain = new_scheme["properties"][0]["addresses"][0]
                new_chain["chain"] = request.POST["chain"]
                new_chain["update_time"] = time_now()
                new_chain["books"].append({"tag": request.POST["tag"],
                                           "address": request.POST["address"]})
                myauths.update_one({"username": request.session['username']},
                                   {'$addToSet':
                                        {"schemes.$[item].properties.$[property].addresses": new_chain
                                         #         {
                                         #     "chain": request.POST["chain"],
                                         #     "amount": 0.0,
                                         #     "update_time": time_now(),
                                         #     "withdrawAmount": 0.0,
                                         #     "books": [{"tag": request.POST["tag"], "address": request.POST["address"]}]
                                         # }
                                         }
                                    },
                                   upsert=True,
                                   array_filters=[
                                       {"item.id": float(request.POST["id"])},
                                       {"property.symbol": request.POST["coin"]},
                                   ]
                                   )  # 用addToSet以便避免添加重复数据
    else:  # 查到了chain，直接添加
        myauths.update_one({"username": request.session['username']},
                           {'$addToSet': {"schemes.$[item].properties.$[property].addresses.$[address].books": {
                               "tag": request.POST["tag"], "address": request.POST["address"]}}},
                           upsert=True,
                           array_filters=[
                               {"item.id": float(request.POST["id"])},
                               {"property.symbol": request.POST["coin"]},
                               {"address.chain": request.POST["chain"]},
                           ]
                           )  # 用addToSet以便避免添加重复数据
    return json_wrap(output)

@check_login
@check_parameters(["chain", "coin", "id", "address", "tag"])
def deleteAddressBook(request):
    output = {"status": 200, "msg": "Address has been successfully deleted!"}
    query = list(myauths.find({"username": request.session["username"],
                               "schemes": {  # 多级嵌套写法！
                                   "$elemMatch": {
                                       "properties": {
                                           "$elemMatch": {
                                               "symbol": request.POST["coin"],
                                               "addresses.chain": request.POST["chain"],
                                           }
                                       },
                                       "id": float(request.POST["id"]),
                                   }
                               }}, {"username": 1, "schemes.id": 1, "schemes.properties":1,"_id": 0}))
    # 查询id方案中用户的chainAddresses数组中现在是否存在name为chain这个对象，不存在返回空数组
    if len(query) == 0:  # 如果查到了这个chain的存在，则直接添加，否则查币和链存不存在,不存在返回错误，存在的话向用户数据里添加信息
        output = {"status": 500, "msg": "Sorry, we cannot find specified coin or chain info!"}
    else:  # 查到了chain，直接添加
        try:
            # properties = list(filter(lambda x: x["id"] == float(request.POST["id"]), query[0]["schemes"]))[0][
            #     "properties"]
            # addresses = list(filter(lambda x: x["symbol"] == request.POST["coin"],properties))[0]["addresses"]
            myauths.update_one({"username": request.session['username']},
                               {'$pull': {"schemes.$[item].properties.$[property].addresses.$[address].books": {
                                   "tag": request.POST["tag"], "address": request.POST["address"]}}},
                               upsert=True,
                               array_filters=[
                                   {"item.id": float(request.POST["id"])},
                                   {"property.symbol": request.POST["coin"]},
                                   {"address.chain": request.POST["chain"]},
                               ]
                               )

        except:
            output = {"status": 500, "msg": "Sorry, we cannot find specified address info!"}


    return json_wrap(output)


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
    new_scheme = copy.deepcopy(scheme_template)
    new_scheme["id"] = new_scheme_id
    new_scheme["name"] = new_scheme_name
    new_scheme["create_time"] = time_now()
    new_scheme["properties"][0]["addresses"][0]["update_time"] = time_now()
    new_scheme["investPlans"][0]["create_time"] = time_now()
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
    pass

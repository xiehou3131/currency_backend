import random
import string
from datetime import datetime
import os
from django.http import HttpResponse
import json
from functools import wraps
from .dbconfig import *
from bson import json_util
from .tools import *
from django.core.cache import cache

from .view import check_login, check_parameters


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
def getSchemeChart(request):
    schemeChartLogs = list(myauths.find({"username": request.session["username"]},
                                        {"schemes.propertyLogs": {
                                            "$slice": [-4400, 4400]  # 最多返回一年的log
                                        }, "username": 1, "schemes.id": 1, "schemes.name": 1, "_id": 0}))[
        0]  # 得到用户所有方案的propertyLogs，按数量算好的
    output = {}
    for scheme in schemeChartLogs['schemes']:  # 输出指定scheme的信息
        if scheme["id"] == float(request.GET['id']):
            output = scheme
    return json_wrap({"status": 200, "data": output})


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
    return json_wrap({"status": 200, "data": output})


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

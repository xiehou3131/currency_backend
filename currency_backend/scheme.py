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
from .email import send_mail

from .view import check_login, check_parameters

@check_login
def getSchemeMenu(request):
    # num = list(myauths.aggregate(
    #     [{'$match': {'username': request.session["username"]}},
    #      {'$project': {'count': {"$size": '$schemes'}}}
    #      ])) # 查询scheme数组内元素的个数，即有几套方案
    menus = myauths.find({"username": request.session["username"]},
                         {"schemes.id": 1
        , "username": 1, "schemes.name": 1, "_id": 0})  # 得到用户所有方案的investPlans，按数量算好的
    return json_wrap({"status": 200, "data": menus}, no_log=True)

import json
import re
import pymongo
from bson import Regex

myclient = pymongo.MongoClient('mongodb://currency:Qw123456789@localhost:27017/',connect=False)
mydb = myclient['currency']
myauths = mydb["userInfo"]
logs = mydb["logs"]
coin = mydb["coinInfo"]
# {
#   $project: {
#     _id: 1,
#     product: 1,
#     money: 1,
#     name: 1
#   }
# }
# https://blog.csdn.net/u011113654/article/details/80353013

# # 展示了如何多表查询并提取指定字段
# models_with_info = models.aggregate(
#     [{'$lookup': {'from': "auths", "localField": "author", "foreignField": "username", "as": "author_info"}},
#      {'$unwind': {'path': '$author_info', 'preserveNullAndEmptyArrays': True}},
#      {'$addFields': {'nickname': "$author_info.nickname"}},
#      {'$project': {'author_info': 0}}
#      ])

# 生成简单查询条件
def getQueryCondition(queryConditions):
    conditions = []
    for fieldInfo in queryConditions:
        if fieldInfo["type"] == 'text' or fieldInfo["type"] == 'array' or fieldInfo["type"] == 'datetime':
            pattern = re.compile(r'.*' + fieldInfo['query'] + '.*', re.I)
            regex = Regex.from_native(pattern)
            regex.flags ^= re.UNICODE
            conditions.append({fieldInfo["name"]: regex})
        elif fieldInfo["type"] == 'number':
            if fieldInfo["query"] != "":
                try:
                    num = float(fieldInfo["query"])
                    conditions.append({fieldInfo["name"]: {"$eq": num}})
                except:
                    conditions.append({fieldInfo["name"]: {"$eq": -99999}})
            else:
                conditions.append({fieldInfo["name"]: {"$gte": -99999}})
    return {"$or": conditions}

# 【Python有坑系列】函数默认参数_小白兔de窝-CSDN博客
# https://blog.csdn.net/ztf312/article/details/84998137
# 根据不同条件查询
def queryTable(table, request, additionalColumns={"_id": 0}, additionalConditions=None, aggregationConditions=False):
    if additionalConditions is None:
        additionalConditions = []
    pageNum = int(request.POST["pageNum"])
    pageSize = int(request.POST["pageSize"])
    queryConditions = json.loads(request.POST["fields"])
    conditions = getQueryCondition(queryConditions)
    if 'advance' in request.POST and request.POST['advance'] == '1':
        queryFields = json.loads(request.POST["queryFields"])
        multiConditions = json.loads(request.POST["multiConditions"])
        for field in queryFields:
            if field['type'] == 'datetime':
                datetime_from = multiConditions[field['value'] + "_from"]
                if datetime_from != '':
                    additionalConditions.append({field['value']: {"$gte":  datetime_from.replace("T"," ")}})
                datetime_to = multiConditions[field['value'] + "_to"]
                if datetime_to != '':
                    additionalConditions.append({field['value']: {"$lte": datetime_to.replace("T", " ")}})
            elif field['type'] == 'number':
                try:
                    num_from = float(multiConditions[field['value'] + "_from"])
                    additionalConditions.append({field['value']:{"$gte": num_from}})
                except:
                    pass
                try:
                    num_to = float(multiConditions[field['value'] + "_to"])
                    additionalConditions.append({field['value']:{"$lte": num_to}})
                except:
                    pass
            else:
                query_t = multiConditions[field['value']]
                if query_t == '':
                    continue
                pattern_t = re.compile(r'.*' + query_t + '.*', re.I)
                regex_t = Regex.from_native(pattern_t)
                regex_t.flags ^= re.UNICODE
                additionalConditions.append({field['value']: regex_t})
    # CTRL + ALT + SHIFT + J同时选中相同单词
    if aggregationConditions:
        aggregationConditionsT = aggregationConditions.copy()
        if additionalConditions:
            additionalConditions.append(conditions)
            conditions = {"$and": additionalConditions}
        aggregationConditionsT.append({'$match': conditions})
        total = len(table.aggregate(aggregationConditionsT)._CommandCursor__data)
        # 注意顺序，应该先sort再skip和limit！！！
        aggregationConditionsT.append({"$sort": {request.POST["sortProp"]: int(request.POST["order"])}})
        aggregationConditionsT.append({'$skip': pageSize * (pageNum - 1)})
        aggregationConditionsT.append({"$limit": pageSize})
        result = list(table.aggregate(aggregationConditionsT))
    else:
        # 如果有额外的查询条件，使用and语句加入条件
        if additionalConditions:
            additionalConditions.append(conditions)
            query = table.find({"$and": additionalConditions}, additionalColumns)
        # 没有额外的查询条件，直接查询
        else:
            query = table.find(conditions, additionalColumns)
        sortCondition = [(request.POST["sortProp"], int(request.POST["order"]))]
        # .collation({"locale": "en"})不区分大小写
        query.sort(sortCondition).skip(pageSize * (pageNum - 1)).limit(pageSize).collation({"locale": "en"})
        result = list(query)
        total = query.count()
    return result, total

import pymongo

from currency_backend.tools import time_now

if __name__ == '__main__':
    myclient = pymongo.MongoClient('mongodb://currency:Qw123456789@localhost:27017/', connect=False)
    mydb = myclient['currency']
    myauths = mydb["userInfo"]
    coin = mydb["coinInfo"]
    query = list(myauths.find({"username": "naibowang@comp.nus.edu.sg",
                        "schemes": { # 多级嵌套写法！
                            "$elemMatch": {
                                "properties":{
                                    "$elemMatch":{
                                        "symbol": "USDT",
                                        "addresses.chain": "1BEP20 (BSC)",
                                    }
                                },
                                "id":1,
                            }
                        }}, {"username": 1, "schemes.id": 1, "_id": 0}))
    print(query)
    query = list(myauths.find({"username": "naibowang@comp.nus.edu.sg",
                               "schemes": {  # 多级嵌套写法！
                                   "$elemMatch": {
                                       "properties.symbol": "ETHs",
                                       "id": 1,
                                   }
                               }}, {"username": 1, "schemes.id": 1, "_id": 0}))
    print(query)
    queryChain = list(coin.find({"symbol": "USDTsdf",
                                 "supportChains": {  # 多级嵌套写法！
                                     "$elemMatch": {
                                         "name": "OMNI",
                                     }
                                 }}, {"_id": 0}))
    print(queryChain)
    myauths.update_one({"username": "naibowang@comp.nus.edu.sg"},
                       {'$addToSet':
                            {"schemes.$[item].properties":
                                {"symbol": "test", "addresses": [{
                                                               "chain": "etc",
                                                               "amount": 0,
                                                               "update_time": time_now(),
                                                               "withdrawAmount": 0,
                                                               "books": [{"tag": 1, "address": 2}]}]}}},
                       upsert=True,
                       array_filters=[
                           {"item.id": 1},
                       ]
                       )  # 用addToSet以便避免添加重复数据
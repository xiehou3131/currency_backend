"""
User info management (login, register, check_login, etc)
"""
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


def hello(request):
    return json_wrap({"msg": "Hello world!"}, no_log=True)


def S04(request, exception):  # 404页面
    return json_wrap({"msg": "404!"}, no_log=True)


def S500(request):
    import traceback
    error = str(traceback.format_exc())
    return json_wrap({"status": 500, "msg": "Server Internal Error!", "info": error}, no_log=True)


def check_login(f):
    @wraps(f)
    def inner(request, *arg, **kwargs):
        if request.session.get('is_login') == '1':
            return f(request, *arg, **kwargs)
        else:
            return HttpResponse(json.dumps({"status": 302, "msg": "Not logged in!"}),
                                content_type="application/json")

    return inner


def check_manager(f):
    @wraps(f)
    def inner(request, *arg, **kwargs):
        if request.session.get('role') == 'manager':
            return f(request, *arg, **kwargs)
        else:
            return HttpResponse(json.dumps({"status": 302, "msg": "Sorry, you don't have permission to do this!"}),
                                content_type="application/json")

    return inner


# 查找参数是否在请求中
def check_parameters(paras):
    def _check_parameter(f):
        @wraps(f)
        def inner(request, *arg, **kwargs):
            for para in paras:
                if para in request.GET or para in request.POST:
                    continue
                else:
                    return NoLogHTTPResponse(
                        json.dumps({"status": 400, "msg": "Not specify required parameters: " + para + "!"}),
                        content_type="application/json")
            return f(request, *arg, **kwargs)

        return inner

    return _check_parameter


def getIdentity(request):
    if request.session.get('is_login') == '1':
        return NoLogHTTPResponse(
            json.dumps({"status": 200, "role": request.session["role"], "nickname": request.session["nickname"],
                        "profile": request.session["profile"], "username": request.session["username"],
                        "time": time_now().strftime("%Y-%m-%d %H:%M:%S")}),
            content_type="application/json")
    else:
        print(time_now())
        return NoLogHTTPResponse(
            json.dumps({"status": 200, "role": "guest", "nickname": "guest", "username": "guest",
                        "time": time_now().strftime("%Y-%m-%d %H:%M:%S")}),
            content_type="application/json")


@check_login
def getUserInfo(request):
    result = myauths.find({"username": request.session['username']}, {"pswd": 0, "schemes": 0})
    return json_wrap({"status": 200, "data": list(result)[0]}, no_response=True)


@check_parameters(["query", "pageNum", "pageSize", "fields", "sortProp", "order"])
def getUserList(request):
    if request.session.get('role') == 'manager':
        result, total = queryTable(myauths, request, additionalColumns={"pswd": 0, "_id": 0})
        return json_wrap({"status": 200, "data": list(result), "total": total}, no_response=True)
    else:
        return HttpResponse(
            json.dumps({"status": 303, "msg": "Sorry, you don't have permission to check this list!"}),
            content_type="application/json")


@check_login
@check_parameters(["status", 'id'])
def changeUserStatus(request):
    res = myauths.find({"id": int(request.GET['id'])})
    r = list(res)
    if len(r) == 0:  # 没找到值
        result = {"status": 404, "msg": "User not found!"}
    elif r[0]["role"] == 'manager':
        result = {"status": 305, "msg": "Sorry, manager cannot be disabled!"}
    else:
        if request.GET["status"] == "true":
            status = True
        else:
            status = False
        myauths.update_one({"id": int(request.GET["id"])}, {'$set': {"status": status}})
        if status:
            msg = "Normal"
        else:
            msg = "Disabled"
        result = {"status": 200, "msg": "User status has been successfully set to " + msg}
    return HttpResponse(json.dumps(result), content_type="application/json")


@check_login
@check_parameters(["nickname"])
def changeUserInfo(request):
    myauths.update_one({"username": request.session["username"]},
                       {'$set': {"nickname": request.GET['nickname'], 'profile': request.GET['profile']}})
    request.session['nickname'] = request.GET['nickname']
    request.session["profile"] = request.GET['profile']
    return HttpResponse(json.dumps({"status": 200, "msg": "User info change successfully!"}),
                        content_type="application/json")


@check_manager
@check_parameters(['id'])
def resetPassword(request):
    res = myauths.find({"id": int(request.GET['id'])})
    r = list(res)
    if len(r) == 0:  # 没找到值
        result = {"status": 404, "msg": "User not found!"}
    elif r[0]["role"] == 'manager':
        result = {"status": 305, "msg": "Sorry, manager's password cannot be reset!"}
    else:
        myauths.update_one({"id": int(request.GET["id"])}, {'$set': {"pswd": 'qq'}})
        result = {"status": 200, "msg": "User password has been successfully set to 'qq'"}
    return HttpResponse(json.dumps(result), content_type="application/json")


def resetPasswordUser(request):
    if not_email(request.POST['username']):
        return HttpResponse(
            json.dumps({"status": 401, "msg": "The email address format is not correct!"}),
            content_type="application/json")
    result = myauths.find({"username": request.POST['username']})
    r = list(result)
    if len(r) != 0:  # 找到了用户
        if cache.has_key(request.POST['username']):  # 如果没过期，则判断
            # 如果验证码输入正确,注意这里如果验证码的键过期了值也是false，所以不用专门做has_key的判断 （但下面的incr函数不能用，所以还是加了has_key)
            if cache.get(request.POST['username']) == request.POST["captcha"] and cache.get(
                    request.POST['username'] + "_test") < 5:
                myauths.update_one({"username": request.POST['username']},
                                   {'$set': {"pswd": decrypt_message(request.POST['pass'])}})
                cache.delete(request.POST['username'])  # 清除验证码
                cache.delete(request.POST['username'] + "_test")
                cache.delete(request.POST['username'] + "_last")
                return HttpResponse(json.dumps({"status": 200, "msg": "Password reset success, please log in!"}),
                                    content_type="application/json")
            else:
                # 注意这里是==则键不存在的时候也照样返回false，如果是>=5则键不存在时会报错，因为会比较NoneType和Int
                if cache.get(request.POST['username'] + "_test") >= 5:
                    return NoRequestLogHTTPResponse(json.dumps({"status": 401,
                                                                "msg": "You have entered too many wrong captchas, please get a new captcha!"}),
                                                    content_type="application/json")
                else:
                    cache.incr(request.POST['username'] + "_test")  # 验证码错误次数+1
                    return NoRequestLogHTTPResponse(
                        json.dumps({"status": 401, "msg": "Sorry, the captcha you entered is not correct!"}),
                        content_type="application/json")
        else:
            return NoRequestLogHTTPResponse(
                json.dumps({"status": 401, "msg": "Sorry, the captcha has expired, please get a new captcha!"}),
                content_type="application/json")
    else:
        return NoRequestLogHTTPResponse(
            json.dumps({"status": 404, "msg": "User not found!"}),
            content_type="application/json")


@check_parameters(["username", "pass"])
def login(request):
    result = myauths.find({"username": request.POST['username']})
    r = list(result)
    if len(r) == 0:  # 没找到值
        result = {"status": 404, "msg": "User not found!"}
    else:
        item = r[0]
        password = decrypt_message(request.POST['pass'])
        if item["pswd"] != password:
            result = {"status": 201, "msg": "Wrong password!"}
        elif not item["status"]:
            result = {"status": 202, "msg": "Sorry, this account has been disabled!"}
        else:
            result = {"status": 200, "role": item["role"], 'msg': 'Login Success!'}
            request.session['is_login'] = '1'
            request.session["username"] = request.POST["username"]
            request.session["nickname"] = item["nickname"]
            request.session["role"] = item["role"]
            request.session["profile"] = item["profile"]
            request.session.set_expiry(1200)
    return NoRequestLogHTTPResponse(json.dumps(result), content_type="application/json")


@check_login
def logout(request):
    request.additionalInfo = {"username": request.session["username"],
                              "nickname": request.session["nickname"],
                              "role": request.session["role"]}
    request.session.flush()
    return HttpResponse(json.dumps({"status": 200, "msg": "Logout success!"}), content_type="application/json")


@check_login
def changePassword(request):
    result = myauths.find({"username": request.session["username"]})
    r = list(result)
    if r[0]["pswd"] == decrypt_message(request.POST["oldPass"]):
        myauths.update_one({"username": request.session["username"]},
                           {'$set': {"pswd": decrypt_message(request.POST['pass'])}})
        logout(request)
        return NoRequestLogHTTPResponse(json.dumps({"status": 200}), content_type="application/json")
    else:
        return NoRequestLogHTTPResponse(json.dumps({"status": 401, "msg": "Old password is not correct!"}),
                                        content_type="application/json")


def register(request):
    if not_email(request.POST['username']):
        return NoRequestLogHTTPResponse(
            json.dumps({"status": 401, "msg": "The email address format is not correct!"}),
            content_type="application/json")
    result = myauths.find({"username": request.POST['username']})
    r = list(result)
    if len(r) == 0:  # 没找到值
        if cache.has_key(request.POST['username']):  # 如果没过期，则判断
            # 如果验证码输入正确,注意这里如果验证码的键过期了值也是false，所以不用专门做has_key的判断 （但下面的incr函数不能用，所以还是加了has_key)
            if cache.get(request.POST['username']) == request.POST["captcha"] and cache.get(
                    request.POST['username'] + "_test") < 5:
                user = {"username": request.POST['username'], "pswd": decrypt_message(request.POST['pass']),
                        "role": "user",
                        "status": True, "register_time": datetime.utcnow(), "nickname": request.POST['nickname'],
                        "profile": "user.png", "schemes": {}}
                myauths.insert_one(user)
                cache.delete(request.POST['username'])  # 清除验证码
                cache.delete(request.POST['username'] + "_test")
                cache.delete(request.POST['username'] + "_last")
                return HttpResponse(json.dumps({"status": 200, "msg": "Register success, please log in!"}),
                                    content_type="application/json")
            else:
                # 注意这里是==则键不存在的时候也照样返回false，如果是>=5则键不存在时会报错，因为会比较NoneType和Int
                if cache.get(request.POST['username'] + "_test") >= 5:
                    return NoRequestLogHTTPResponse(json.dumps({"status": 401,
                                                                "msg": "You have entered too many wrong captchas, please get a new captcha!"}),
                                                    content_type="application/json")
                else:
                    cache.incr(request.POST['username'] + "_test")  # 验证码错误次数+1
                    return NoRequestLogHTTPResponse(
                        json.dumps({"status": 401, "msg": "Sorry, the captcha you entered is not correct!"}),
                        content_type="application/json")
        else:
            return NoRequestLogHTTPResponse(
                json.dumps({"status": 401, "msg": "Sorry, the captcha has expired, please get a new captcha!"}),
                content_type="application/json")
    else:
        return NoRequestLogHTTPResponse(
            json.dumps({"status": 210, "msg": "The email address has already been registered"}),
            content_type="application/json")


def getCaptcha(request):
    if not_email(request.POST['username']):  #
        return NoRequestLogHTTPResponse(
            json.dumps({"status": 401, "msg": "The email address format is not correct!"}),
            content_type="application/json")
    result = myauths.find({"username": request.POST['username']})
    r = list(result)
    if len(r) == 0 or request.POST['reset'] == '1':  # 没找到用户邮箱或者找到了但是用户是在重置密码, 不管前端格式如何，后台得到的永远都是字符串！
        if cache.has_key(request.POST['username'] + "_last"):  # 如果在60秒以内想要再次请求验证码，再等等
            return NoRequestLogHTTPResponse(
                json.dumps({"status": 401, "msg": "Please wait for at least 60 seconds to get a new captcha!"}),
                content_type="application/json")
        else:
            wt = 60  # wait time
            cache.set(request.POST['username'] + "_last", "1", wt)  # 设置等待键时长
            cache.set(request.POST['username'] + "_test", 1, wt * 5)  # 设置验证码验证次数
            captcha = "".join(random.sample([x for x in string.digits], 6))
            cache.set(request.POST['username'], captcha, wt * 5)
            send_mail([request.POST['username']], 'Currency Market <validator@currencymarket.naibo.wang>',
                      'Captcha from Currency Market', """<html>
  <head></head>
  <body>
    <p>Hello, your captcha is: <strong>%s</strong>, please enter in 5 minutes.
    <br>This is an automatically generated email, please do not respond. :)
    </p>
  </body>
</html>""" % cache.get(request.POST['username']  # 三个双引号保证不需要换行标记\就可以实现多行输出的效果，不然每行最后都需要加一个\
                       ), [])
            # 发送邮箱操作
        return HttpResponse(
            json.dumps({"status": 200,
                        "msg": "The captcha has been sent to your mailbox, please check (both Inbox and Junk mailbox)!"}),
            content_type="application/json")
    else:
        return NoRequestLogHTTPResponse(
            json.dumps({"status": 210, "msg": "The email address has already been registered"}),
            content_type="application/json")


@check_login
def uploadFile(request):
    try:
        file_obj = request.FILES.get('file')
        file_extension = file_obj.name.split(".")[-1]
        if file_extension in ['png', 'svg', 'jpg', 'jpeg', 'bmp', 'gif']:
            file_type = 'image'
        else:
            file_type = 'file'
        filename = request.session["username"] + "_" + file_type + "_" + time_now().strftime(
            "_%Y-%m-%d-%H-%M-%S") + str(random.random() * 10).replace(".", '') + '.' + file_extension
        if file_type == "image":
            f = open(os.getcwd() + "/static/pics/" + filename, 'wb')
        else:
            f = open(os.getcwd() + "/static/files/" + filename, 'wb')
        for chunk in file_obj.chunks():
            f.write(chunk)
        f.close()

        return json_wrap({"status": 200, "filename": filename, 'file_type': file_type})
    except Exception as e:
        return HttpResponse(json.dumps({"status": 500, "msg": str(e)}), content_type="application/json")

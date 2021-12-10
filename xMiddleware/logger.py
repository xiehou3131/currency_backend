import datetime
import json
import logging
import threading
import socket
from bson import json_util
from currency_backend.dbconfig import *
from currency_backend.tools import time_now

from django.utils.deprecation import MiddlewareMixin

local = threading.local()
from ipware import get_client_ip


def beijing(sec, what):
    beijing_time = datetime.datetime.now() + datetime.timedelta(hours=8)
    return beijing_time.timetuple()


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


logging.Formatter.converter = beijing


class RequestLogFilter(logging.Filter):
    """
    日志过滤器
    """

    def filter(self, record):
        record.sip = getattr(local, 'sip', 'none')
        record.dip = getattr(local, 'dip', 'none')
        record.body = getattr(local, 'body', 'none')
        record.path = getattr(local, 'path', 'none')
        record.method = getattr(local, 'method', 'none')
        record.username = getattr(local, 'username', 'none')
        record.role = getattr(local, 'role', 'none')
        record.nickname = getattr(local, 'nickname', 'none')
        record.status_code = getattr(local, 'status_code', 'none')
        record.response = getattr(local, 'response', 'none')
        record.reason_phrase = getattr(local, 'reason_phrase', 'none')

        return True


class RequestLogMiddleware(MiddlewareMixin):
    """
    将request的信息记录在当前的请求线程上。
    """

    def __init__(self, get_response=None):
        self.get_response = get_response
        self.apiLogger = logging.getLogger('web.log')

    def __call__(self, request):
        response = self.get_response(request)
        if hasattr(response, 'no_log'):
            return response
        try:
            body = json.loads(request.body)
        except Exception:
            body = dict()

        if request.method == 'GET':
            body.update(dict(request.GET))
        else:
            body.update(dict(request.POST))
        local.__dict__.clear()  # used in production multi-threading mode!
        local.time = time_now()
        local.func = request.path.replace("/currency_backend/", "")
        local.method = request.method
        if "username" in request.session:
            local.username = request.session["username"]
        else:
            local.username = "Guest"
        if "role" in request.session:
            local.role = request.session["role"]
        else:
            local.role = "Guest"
        if "nickname" in request.session:
            local.nickname = request.session["nickname"]
        else:
            local.nickname = "Guest"
        if hasattr(request, 'additionalInfo'):
            local.additionalInfo = request.additionalInfo
        if hasattr(response, 'no_request_log'):
            local.request_body = "Not show here to protect information"
        else:
            local.request_body = body
        try:
            local.response = json.loads(bytes.decode(response.content))
            if response.status_code != 200 or hasattr(response, 'no_response_log'):
                local.response = "Not show here to save space"
        except:
            local.response = "Internal Server error, maybe incorrect path."
        local.sip = get_client_ip(request)
        local.dip = socket.gethostbyname(socket.gethostname())
        local.status_code = response.status_code
        local.reason_phrase = response.reason_phrase
        local.help = ""
        self.apiLogger.info('system-auto')
        logs.insert_one(local.__dict__)
        return response

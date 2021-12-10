from tzlocal import get_localzone
from django.http import HttpResponse
from datetime import datetime, timezone, timedelta
from dateutil import parser
import time
from bson import json_util
import json,re
from base64 import b64decode, b16decode
from django.conf import settings


# 不打log的情况
class NoLogHTTPResponse(HttpResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.no_log = True


# 不打request的情况
class NoRequestLogHTTPResponse(HttpResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.no_request_log = True


# 不打response的情况
class NoResponseLogHTTPResponse(HttpResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.no_response_log = True


def json_wrap(res, no_log=False, no_response=False, no_request=False):
    if no_log:
        return NoLogHTTPResponse(json.dumps(res, default=json_util.default), content_type="application/json")
    elif no_response:
        return NoResponseLogHTTPResponse(json.dumps(res, default=json_util.default), content_type="application/json")
    elif no_request:
        return NoRequestLogHTTPResponse(json.dumps(res, default=json_util.default), content_type="application/json")
    else:
        return HttpResponse(json.dumps(res, default=json_util.default), content_type="application/json")


def time_now():
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    obj = utc_now.astimezone(timezone(timedelta(hours=8)))
    obj = datetime(obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second, obj.microsecond)
    return obj


def get_time_int():
    return str(int(round(time.time() * 1000)))


def decrypt_message(message):
    decode_data = b64decode(message)
    if len(decode_data) == 127:
        hex_fixed = '00' + decode_data.hex()
        decode_data = b16decode(hex_fixed.upper())
    return bytes.decode(settings.CIPHER.decrypt(decode_data, "ERROR"))

def not_email(userName):
    if re.match(r'^[0-9a-zA-Z_.-]+[@][0-9a-zA-Z_.-]+([.][a-zA-Z]+){1,2}$', userName):
        return False
    else:
        return True

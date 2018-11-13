'''
此部分代码改写自Tencent Common OCR SDK for Python。
'''

#-*- coding: UTF-8 -*-
import hashlib
import urllib.request, urllib.parse, urllib.error
import base64
import json
import time

def setParams(array, key, value):
    '''设置dict键值对'''
    array[key] = value

def getBase64String(image):
    '''获取base64编码的字符串。''' 
    with open(image, 'rb') as f:
        image_data = f.read()
    image_data = base64.b64encode(image_data)
    return image_data.decode() # 在python3中，得到的结果为bytes，需要转换显式为str

def genSignString(parser):
    '''计算签名信息'''
    uri_str = '' # initialized empty string
    for key in sorted(parser.keys()): # 升序拼接
        if key == 'app_key': # app key不参与计算
            continue
        # 字符串转为ASCII，无保留字符，注意int2str。
        uri_str += "%s=%s&" % (key, urllib.parse.quote(str(parser[key]), safe = ''))
    sign_str = uri_str + 'app_key=' + parser['app_key'] # 最后拼接app key
    hash_md5 = hashlib.md5(sign_str.encode()) # 计算hash md5值，需要str2bytes
    return hash_md5.hexdigest().upper()
 

class AiPlat(object):
    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key
        self.url_preffix = 'https://api.ai.qq.com/fcgi-bin/'
        self.url = None
        self.data = {}

    def invoke(self, params):
        self.url_data = urllib.parse.urlencode(params)
        self.url_data = self.url_data.encode() # 请求所用的数据，需要str2bytes
        req = urllib.request.Request(self.url, self.url_data) # 请求头
        try:
            rsp = urllib.request.urlopen(req) # 回应
            str_rsp = rsp.read()
            dict_rsp = json.loads(str_rsp)
            return dict_rsp
        
        except urllib.error.URLError as e:
            dict_error = {}
            if hasattr(e, "code"):
                dict_error = {}
                dict_error['ret'] = -1
                dict_error['httpcode'] = e.code
                dict_error['msg'] = "sdk http post err"
                return dict_error
            if hasattr(e, "reason"):
                dict_error['msg'] = 'sdk http post err'
                dict_error['httpcode'] = -1
                dict_error['ret'] = -1
                return dict_error
            else:
                dict_error = {}
                dict_error['ret'] = -1
                dict_error['httpcode'] = -1
                dict_error['msg'] = "system error"
                return dict_error

    def getOcrGeneralocr(self, image):
        '''获取并设置键值对数据，得到签名字符串，添加键值对'''
        self.url = self.url_preffix + 'ocr/ocr_generalocr'
        setParams(self.data, 'app_id', self.app_id)
        setParams(self.data, 'app_key', self.app_key)
        setParams(self.data, 'time_stamp', int(time.time()))
        setParams(self.data, 'nonce_str', int(time.time()))
        image_data = getBase64String(image) # base64 encoded string
        setParams(self.data, 'image', image_data)
        sign_str = genSignString(self.data)
        setParams(self.data, 'sign', sign_str)
        return self.invoke(self.data) # self.data is a dict


#!/usr/bin/env python
#-*- coding: utf-8 -*-
#系统API类

from flask import make_response, request, current_app, url_for
from flask import g
from .authentication import auth
from . import api
from .decorators import permission_required
from ..models import Permission, User, Appointment
from ..core.common import jsonify
from ..core import common
from ..sdk import tencentyun
from config import config
from .. import conf
import time


@api.route('/sys/list')
#@permission_required(Permission.DISCOVERY)
def get_sys_class():
    '''
    获取领域和行业数据

    URL:/sys/list
    GET 参数:
        无
    '''
    return jsonify(domain=conf.DOMAIN, industry=conf.INDUSTRY)

@api.route('/sys/img_sign/<int:_type>')
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def QCLOUD_get_app_sign_v2(_type=0):
    '''
    获取上传签名(万象优图)

    用户:会员
    URL:/sys/img_sign/<int:_type>
    GET 参数:
    _type -- 图片类型 1头像 2简介图片或视频
    返回值
        sign
    '''
    if _type==0:
        return ''
    # 生成上传签名
    q_auth = tencentyun.Auth(conf.QCLOUD_SECRET_ID,conf.QCLOUD_SECRET_KEY)

    if _type==1:
        fileid = 'avatar_'
    elif _type==2:
        fileid = 'introfile_'
    expired = int(time.time()) + 999
    sign = q_auth.get_app_sign_v2(bucket=conf.QCLOUD_BUCKET, fileid='',expired=expired)
    return jsonify(sign=sign)

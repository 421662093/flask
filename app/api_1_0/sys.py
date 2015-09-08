#!/usr/bin/env python
#-*- coding: utf-8 -*-
#系统API类

from flask import make_response, request, current_app, url_for
from flask import g
from .authentication import auth
from . import api
from .decorators import permission_required
from ..models import Permission, User,UserOpenPlatform, Appointment
from ..core.common import jsonify
from ..core import common
from ..sdk import tencentyun
from config import config
from .. import conf
import logging
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

'''
bug 修复

@api.route('/sys/init')
def sys_init():
    uid = request.args.get('uid',0)
    u1 = request.args.get('u1','')
    u2 = request.args.get('u2','')
    u3 = request.args.get('u3','')
    u4 = request.args.get('u4','')
    u5 = request.args.get('u5','')
    u6 = request.args.get('u6','')
    u7 = request.args.get('u7','')
    if uid>0:

        user = User()
        u_sp_1 = UserOpenPlatform()
        u_sp_2 = UserOpenPlatform()
        u_sp_3 = UserOpenPlatform()
        u_sp_4 = UserOpenPlatform()
        u_sp_5 = UserOpenPlatform()
        u_sp_6 = UserOpenPlatform()
        u_sp_7 = UserOpenPlatform()

        u_sp_1.name = 'baidu'
        u_sp_1.url = len(u1)>5 and u1 or ''

        u_sp_2.name = 'weixin'
        u_sp_2.url = len(u2)>5 and u2 or ''

        u_sp_3.name = 'zhihu'
        u_sp_3.url = len(u3)>5 and u3 or ''

        u_sp_4.name = 'sina'
        u_sp_4.url = len(u4)>5 and u4 or ''

        u_sp_5.name = 'twitter'
        u_sp_5.url = len(u5)>5 and u5 or ''

        u_sp_6.name = 'facebook'
        u_sp_6.url = len(u6)>5 and u6 or ''

        u_sp_7.name = 'github'
        u_sp_7.url = len(u7)>5 and u7 or ''

        user.openplatform.append(u_sp_1)
        user.openplatform.append(u_sp_2)
        user.openplatform.append(u_sp_3)
        user.openplatform.append(u_sp_4)
        user.openplatform.append(u_sp_5)
        user.openplatform.append(u_sp_6)
        user.openplatform.append(u_sp_7)
        update = {}
        update['set__openplatform'] = user.openplatform
        User.objects(_id=uid).update_one(**update)
        logging.debug('uid='+str(uid)+'u1='+u1+'u2='+u2+'u3='+u3+'u4='+u4+'u5='+u5+'u6='+u6+'u7='+u7)
    return jsonify(u1=u1,u2=u2,u3=u3,u4=u4,u5=u5,u6=u6,u7=u7)

@api.route('/sys/repair')
#@permission_required(Permission.DISCOVERY)
def sys_repair():

    import httplib

    u_list = User.getlist(index=1,count=300)
    for item in u_list:
        httpClient = None
        try:
            httpClient = httplib.HTTPConnection('182.254.221.13', 8080, timeout=20)
            httpClient.request('GET', '/api/v1.0/sys/init?uid='+str(item._id)+'&u1='+item.stats.baiduurl+'&u2'+item.stats.weixinurl+'&u3'+item.stats.zhihuurl+'&u4'+item.stats.sinaurl+'&u5'+item.stats.twitterurl+'&u6'+item.stats.facebookurl+'&u7'+item.stats.githuburl)
            #response是HTTPResponse对象
            response = httpClient.getresponse()
            print response.status
            print response.reason
            print response.read()
        except Exception, e:
            print e
        finally:
            if httpClient:
                httpClient.close()
'''
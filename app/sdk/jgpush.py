#!/usr/bin/env python
#-*- coding: utf-8 -*-

import jpush as jgpush
from .. import conf
import logging
from ..core import common
# 推送消息
# @param alert  必选参数  消息内容
# @param msg  必选参数  自定义参数  {'k1':'v1'}
def pushmessage(jpush,alert,msg,alias):

    try:
        _jpush = jpush.JPush(conf.JPush_API_KEY, conf.JPush_MASTER_SECRET)
        push = _jpush.create_push()
        push.audience = len(alias)==0 and jpush.all_ or {"alias" : alias}
        ios_msg = jpush.ios(alert=alert, sound="a.caf",badge="+1", extras=msg)#
        push.notification = jpush.notification(alert="口袋专家", android={}, ios=ios_msg)
        push.options = {"time_to_live":86400, "sendno":common.getrandom(10000000,99999999),"apns_production":True}
        push.platform = jpush.platform("ios")
        push.send()
    except Exception,e:
        logging.debug(e)
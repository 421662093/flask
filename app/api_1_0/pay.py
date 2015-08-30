#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import jsonify, request, current_app, url_for
from . import api
#from ..core import wxpayapi
import pingpp
import json
from ..models import Appointment,PayLog
from ..core import common
from .. import conf
#from ..getuipush import *

'''
@api.route('/pay/getpayid')
def get_payid():
    order = wxpayapi.UnifiedOrder_pub()
    order.parameters['out_trade_no'] = request.args.get('out_trade_no')
    order.parameters['body'] = request.args.get('body')
    order.parameters['total_fee'] = request.args.get('total_fee')
    order.parameters['notify_url'] = '10000'
    order.parameters['trade_type'] = 'APP'
    order.createXml()
    PrepayId = order.getPrepayId()
    return PrepayId
'''

@api.route('/pay/webhooks')
def get_payid():

    data = request.get_json()
    pay = PayLog()
    pay.created = common.strtoint(data['created'],0)
    pay.paid = data['paid']
    pay.app = data['app']
    pay.channel =  data['channel']
    pay.order_no = data['order_no']
    #client_ip
    pay.amount = common.strtoint(data['amount'],0)
    pay.amount_settle = common.strtoint(data['amount_settle'],0)
    pay.currency = data['currency']
    pay.subject = data['subject']
    pay.body = data['body']
    pay.time_paid = data['time_paid']
    pay.time_expire = data['time_expire']
    pay.transaction_no = data['transaction_no']
    pay.amount_refunded = data['amount_refunded']
    pay.failure_code = data['failure_code']
    pay.failure_msg = data['failure_msg']
    pay.description = data['description']
    pay.saveinfo()

    import jpush as jpush
    _jpush = jpush.JPush('2d85bc2c4cc44f976c26286d', '9e245d142adba0289b329b73')
    push = _jpush.create_push()
    push.audience = jpush.all_
    ios_msg = jpush.ios(alert="Hello, IOS JPush!", badge="+1", sound="a.caf", extras={'k1':'v1'})
    push.notification = jpush.notification(alert="Hello, JPush!", android=android_msg, ios=ios_msg)
    push.options = {"time_to_live":86400, "sendno":12345,"apns_production":True}
    push.platform = jpush.platform("ios")
    push.send()

    return jsonify(ret=1) 

@api.route('/pay/charge', methods=['POST'])
def do_charge():
    '''
    获取支付签名（pingpp）

    URL:/pay/charge
    格式
        JSON
    POST 参数:
        order_no -- 预约订单ID
    返回值
        返回charge JSON对象(pingpp)
    '''
    form = request.get_json()
    orderid = common.strtoint(form['order_no'],0)
    if orderid>0:
        o_info = Appointment.getinfo(orderid)
        if o_info is not None:
            if isinstance(form, dict):
                form['app'] = dict(id=conf.PINGPP_APP_ID)
                form['channel'] = 'alipay'
                form['amount'] = o_info.price
                form['currency'] = "cny"
                form['client_ip'] = "127.0.0.1"
                form['subject'] = '口袋专家充值'
                form['body'] = len(o_info.topic_title)>0 and o_info.topic_title or "口袋专家充值"
            pingpp.api_key = conf.PINGPP_API_KEY
            response_charge = pingpp.Charge.create(api_key=pingpp.api_key, **form)
            return jsonify(response_charge)
    #return Response(json.dumps(response_charge), mimetype='application/json')

#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import jsonify, request, current_app, url_for
from flask import g
from . import api
from .authentication import auth
#from ..core import wxpayapi
import pingpp
import json
from ..models import Appointment,PayLog,Message,User
from ..core import common
from .. import conf
import logging
import jpush as jpush
from ..sdk.jgpush import pushmessage
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

@api.route('/pay/webhooks', methods=['POST'])
def get_payid():

    try:

        data = request.get_json()
        pay = PayLog()
        pay.created = common.strtoint(data['created'],0)
        pay.paid = data['data']['object']['paid']
        pay.app = data['data']['object']['app']
        pay.channel =  data['data']['object']['channel']
        pay.order_no =str(data['data']['object']['order_no'])
        #client_ip
        pay.amount = common.strtoint(data['data']['object']['amount'],0)
        pay.amount_settle = common.strtoint(data['data']['object']['amount_settle'],0)
        pay.currency = data['data']['object']['currency']
        pay.subject = data['data']['object']['subject']
        pay.body = data['data']['object']['body']
        pay.time_paid = data['data']['object']['time_paid']
        pay.time_expire = data['data']['object']['time_expire']
        pay.transaction_no = data['data']['object']['transaction_no']
        pay.amount_refunded = common.strtoint(data['data']['object']['amount_refunded'],0)
        pay.failure_code = data['data']['object']['failure_code']
        pay.failure_msg = data['data']['object']['failure_msg']
        pay.description = data['data']['object']['description']
        pay.saveinfo()
        oid = common.strtoint(data['data']['object']['order_no'],0)
        if oid>10000000000:
            o_info = Appointment.getinfo(pay.order_no)
            if o_info is not None:
                Appointment.updateappstate_app(pay.order_no,3,1) #更新订单状态
                pushmessage(jpush,'口袋专家订单已完成支付',{'type':'update_appointment','app_id':str(pay.order_no),'state':3},[o_info.appid])
        else:

            User.updatemoney(oid,pay.amount)

            msg = Message()
            msg.user_id = oid
            msg.appointment_id = 0
            msg.type = 1
            msg.title = '充值成功'
            msg.content = '您已充值成功。'
            msg.saveinfo()
            pushmessage(jpush,'口袋专家充值已完成支付',{'type':'recharge','state':1},[oid])
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

    return jsonify(ret=1) 

@api.route('/pay/charge', methods=['POST'])
@auth.login_required
def do_charge():
    '''
    获取预约订单支付签名（pingpp）

    URL:/pay/charge
    格式
        JSON
    POST 参数:
        order_no -- 预约订单ID
        channel -- 支付方式
        amount -- 价格
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
                #form['amount'] = o_info.price
                form['currency'] = "cny"
                form['client_ip'] = "127.0.0.1"
                form['subject'] = '口袋专家充值'
                form['body'] = len(o_info.topic_title)>0 and o_info.topic_title or "口袋专家充值"
            pingpp.api_key = conf.PINGPP_API_KEY
            response_charge = pingpp.Charge.create(api_key=pingpp.api_key, **form)
            return jsonify(response_charge)
    #return Response(json.dumps(response_charge), mimetype='application/json')


@api.route('/pay/recharge', methods=['POST'])
@auth.login_required
def do_recharge():
    '''
    获取充值支付签名（pingpp）

    URL:/pay/recharge
    格式
        JSON
    POST 参数:
        channel -- 支付方式
        amount -- 价格
    返回值
        返回charge JSON对象(pingpp)
    '''
    form = request.get_json()
    if isinstance(form, dict):
        form['app'] = dict(id=conf.PINGPP_APP_ID)
        form['order_no'] = g.current_user._id
        form['currency'] = "cny"
        form['client_ip'] = "127.0.0.1"
        form['subject'] = '口袋专家充值'
        form['body'] = "口袋专家充值"
    pingpp.api_key = conf.PINGPP_API_KEY
    response_charge = pingpp.Charge.create(api_key=pingpp.api_key, **form)
    return jsonify(response_charge)
    #return Response(json.dumps(response_charge), mimetype='application/json')

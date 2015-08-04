#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import jsonify, request, current_app, url_for
from . import api
from ..core import wxpayapi


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

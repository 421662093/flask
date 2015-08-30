#!/usr/bin/env python
import pingpp
from .. import conf

pingpp.api_key = conf.PINGPP_API_KEY
extras = dict()

ch = pingpp.Charge.create(
    order_no='123456789',
    channel='alipay',
    amount=1,
    subject='Your Subject',
    body='Your Subject',
    currency='cny',
    app=dict(id='YOUR-APP-ID'),
    client_ip='127.0.0.1'
)
print ch


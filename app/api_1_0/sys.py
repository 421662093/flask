#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import make_response, request, current_app, url_for
from . import api
from .decorators import permission_required
from ..models import Permission, User, Appointment
from ..core.common import jsonify
from ..core import common
from config import config

@api.route('/sys/list')
#@permission_required(Permission.DISCOVERY)
def get_sys_class():
    '''
    获取领域和行业数据

    URL:/sys/list
    GET 参数: 
        无
    '''
    return jsonify(domain=config['default'].DOMAIN, industry=config['default'].INDUSTRY)

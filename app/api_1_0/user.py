#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import make_response, request, current_app, url_for
from . import api
from .decorators import permission_required
from ..models import Permission, User, Appointment,collection
from ..core.common import jsonify
from ..core import common
import json

@api.route('/user/reg', methods = ['POST'])
def new_user():
	data = request.get_json()#{\"name\":\"大撒旦撒\"}
	#print data['username'][0]["c"]
	username = data['username']#request.form.get('username','')
	password = data['password']#request.form.get('password','')

	#if request.data is not None:
	    #username = request.data['username']
	    #password = request.data.password

	if len(username)==0 or len(password)==0:
		return jsonify(ret=-1) #帐号或密码为空
	if User.isusername(username=username)>0:
		return jsonify(ret=-2) #帐号已存在

	col1 = User()
	col1.role_id = 3
	col1.username = username
	col1.password = password
	col1.editinfo()

	return jsonify(ret=1,username=username) #注册成功 ,'token':col1.generate_auth_token(expiration=3600)
	#else:
	#	return jsonify(ret=400)

@api.route('/appointment/list')
@api.route('/appointment/list/<int:_type>')  # _type=1我约 _type=2被约
#@permission_required(Permission.DISCOVERY)
def get_appointment_list(_type=0):  # 预约列表
    a_list = Appointment.getlist(_type=_type, appid=23)
    return jsonify(list=[item.to_json(_type) for item in a_list])


@api.route('/appointment/info/<int:aid>')
@api.route('/appointment/info/<int:aid>/<int:_type>')  # _type=1我约 _type=2被约
#@permission_required(Permission.DISCOVERY)
def get_appointment_info(aid='', _type=1):  # 预约详情
    a_info = Appointment.getinfo(aid=aid)
    return jsonify(app=a_info.to_json(_type, 0))

@api.route('/user/update', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
def update_user_info():  # 更新个人信息
    if request.method == 'POST':
        user = User()
        user._id = request.form.get('_id',1)
        user.name = request.form.get('name','')
        user.sex = request.form.get('sex',1)
        user.useredit()
        return "{'state':1}"

@api.route('/user/thinktank', methods=['GET'])
def get_user_thinktank():
	# 智囊团
    u_info = User.getinfo(uid=73)
    tt_list = User.getthinktanklist_uid(u_info.thinktank)
    if tt_list is not None:
        return jsonify(list=[item.to_json(5) for item in tt_list])
    else:
        return jsonify(list=[])
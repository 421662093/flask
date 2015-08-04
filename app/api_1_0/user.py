#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import make_response, request, current_app, url_for
from . import api
from .decorators import permission_required
from ..models import Permission, User,WorkExp,Edu, Appointment,collection
from ..core.common import jsonify
from ..core import common
import logging
import json

@api.route('/user/reg', methods = ['POST'])
def new_user():
    '''
    注册新用户

    URL:/user/reg
    POST 参数: 
        username -- 帐号 (必填) 
        password -- 密码 (必填) 
    '''
    try: 
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
    except Exception,e:
            logging.debug(e)
            return "{'state':-1}"

@api.route('/user/update', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
def update_user_info():
    '''
    更新个人信息

    URL:/user/update
    POST 参数: 
        _id -- 用户ID (测试时使用，上线后删除)
    	name -- 姓名 (默认 0)
    	sex -- 性别 (默认1,1:男 0:女)
    '''
    if request.method == 'POST':
        try: 
            user = User()
            user._id = request.form.get('_id',1)
            user.name = request.form.get('name','')
            user.sex = request.form.get('sex',1)
            user.useredit()
            return "{'state':1}"
        except Exception,e:
            logging.debug(e)
            return "{'state':-1}"
@api.route('/user/updateworkexp', methods=['GET','POST'])
#@permission_required(Permission.DISCOVERY)
def update_user_workexp():
    '''
    更新工作经历

    URL:/user/updateworkexp
    POST 参数:
    	_id -- 用户ID (测试时使用，上线后删除)
    	list -- 工作经历数组 (由多个工作经历字典组成)
    		start -- 工作起始时间 (必填，时间戳)
    		end -- 工作结束时间 (必填，时间戳)
    		name -- 公司名称 (必填)
    		job -- 职位名称 (必填)
    '''
    if request.method == 'POST':
        try: 
            data = request.get_json()

            _id = data['_id']
            _list = data['list']
            we = []
            user = User()
            user._id = _id
            for item in _list:
                weitem = WorkExp()
                weitem.start = item['start']
                weitem.end = item['end']
                weitem.name = item['name']
                weitem.job = item['job']
                #weitem.intro = '总技术负责移动终端研发'
                we.append(weitem)
            user.workexp = we
            state = user.updateworkexp()
            return "{'state':"+str(state)+"}"
        except Exception,e:
            logging.debug(e)
            return "{'state':-1}"

@api.route('/user/updateedu', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
def update_user_edu():
    '''
    更新教育背景

    URL:/user/updateedu
    POST 参数:
        _id -- 用户ID (测试时使用，上线后删除)
        list -- 工作经历数组 (由多个工作经历字典组成)
            start -- 工作起始时间 (必填，时间戳)
            end -- 工作结束时间 (必填，时间戳)
            name -- 公司名称 (必填)
            job -- 职位名称 (必填)
    '''

    start = db.IntField(default=common.getstamp(),  db_field='s')  # 开始时间
    end = db.IntField(default=common.getstamp(),  db_field='e')  # 结束时间
    name = db.StringField(default='',max_length=64, db_field='n')  # 学校名称
    dip = db.StringField(default='', max_length=40, db_field='d')  # 文凭
    major = db.StringField(default='', db_field='m')  # 专业


    if request.method == 'POST':
        data = request.get_json()

        _id = data['_id']
        _list = data['list']
        we = []
        user = User()
        user._id = _id
        for item in _list:
            weitem = WorkExp()
            weitem.start = item['start']
            weitem.end = item['end']
            weitem.name = item['name']
            weitem.job = item['job']
            #weitem.intro = '总技术负责移动终端研发'
            we.append(weitem)
        user.workexp = we
        state = user.updateworkexp()
        return "{'state':"+str(state)+"}"

@api.route('/appointment/list')
@api.route('/appointment/list/<int:_type>')  # _type=1我约 _type=2被约
#@permission_required(Permission.DISCOVERY)
def get_appointment_list(_type=0):
    '''
	获取用户预约列表

    URL:
    	/appointment/list (_type 为缺省值 1)
    	/appointment/list/<int:_type>
    GET 参数: 
        _type -- 预约类型 (1:我约 2:被约) 
    '''
    a_list = Appointment.getlist(_type=_type, appid=23)
    return jsonify(list=[item.to_json(_type) for item in a_list])


@api.route('/appointment/info/<int:aid>')
@api.route('/appointment/info/<int:aid>/<int:_type>')  # _type=1我约 _type=2被约
#@permission_required(Permission.DISCOVERY)
def get_appointment_info(aid,_type=1):
    '''
    获取用户预约详情

    URL:
        /appointment/info/<int:aid> (_type 为缺省值 1)
        /appointment/info/<int:aid>/<int:_type>
    GET 参数: 
        aid -- 预约ID (默认 0)
        _type -- 预约类型 (1:我约 2:被约) 
    '''
    a_info = Appointment.getinfo(aid=aid)
    return jsonify(app=a_info.to_json(_type, 0))

@api.route('/user/thinktank', methods=['GET'])
def get_user_thinktank():
    '''
    获取用户智囊团列表

    URL:/user/thinktank
    GET 参数: 
        无
    '''
    u_info = User.getinfo(uid=73)
    tt_list = User.getthinktanklist_uid(u_info.thinktank)
    if tt_list is not None:
        return jsonify(list=[item.to_json(5) for item in tt_list])
    else:
        return jsonify(list=[])
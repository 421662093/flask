#!/usr/bin/env python
#-*- coding: utf-8 -*-
#用户API类

from flask import make_response, request, current_app, url_for
from flask import g
from .authentication import auth
from . import api
from .decorators import permission_required
from ..models import Permission, User,WorkExp,Edu, Appointment,Message,collection,Topic,TopicPay
from ..core.common import jsonify
from ..core import common
from .. import mc
import logging
import json
from ..sdk.yuntongxun import SendTemplateSMS as SMS

@api.route('/user/getcode', methods = ['POST'])
def get_code():
    '''
    验证手机号是否存在，并发送手机验证码

    URL:/user/getcode
    POST 参数:
        username -- 帐号 (必填)
    返回值
        {'ret':1} 发送成功
        -1 帐号为空
        -2 帐号已存在
        -3 验证码发送失败,联系运营商
        -4 手机号格式错误
        -5 系统异常
    '''
    try:
        data = request.get_json()
        username = data['username']
        if len(username)==11:
            if len(username)==0:
                return jsonify(ret=-1) #帐号或密码为空
            if User.isusername(username=username)>0:
                return jsonify(ret=-2) #帐号已存在
            code = common.getrandom(100000,999999)
            mc.set('code_'+username,code)
            smscode = SMS.sendTemplateSMS(username,[code],1)
            #print str(type(smscode))+'___'+smscode
            if smscode=='000000':
                return jsonify(ret=1)#验证码已发送
            else:
                return jsonify(ret=-3)#验证码发送失败,联系运营商
        return jsonify(ret=-4)#手机号格式错误
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/user/reg', methods = ['POST'])
def new_user():
    '''
    注册新用户

    URL:/user/reg
    POST 参数:
        username -- 帐号 (必填)
        password -- 密码 (必填)
        code -- 手机验证码 (必填)
    返回值
        {'ret':1,'username':'帐号'} 发送成功
        -1 帐号或密码为空
        -2 帐号已存在
        -3 验证码错误
        -4 手机号格式错误
        -5 系统异常
    '''
    try:
        data = request.get_json()#{\"name\":\"大撒旦撒\"}
        #print data['username'][0]["c"]
        username = data['username']#request.form.get('username','')
        password = data['password']#request.form.get('password','')
        code = data['code']
        #if request.data is not None:
            #username = request.data['username']
            #password = request.data.password

        if len(username)==11:
            if len(username)==0 or len(password)==0:
                return jsonify(ret=-1) #帐号或密码为空
            if User.isusername(username=username)>0:
                return jsonify(ret=-2) #帐号已存在
            rv = mc.get('code_'+username)
            if rv == code:
                col1 = User()
                col1.role_id = 3
                col1.username = username
                col1.password = password
                col1.editinfo()
                return jsonify(ret=1,username=username) #注册成功 ,'token':col1.generate_auth_token(expiration=3600)
            else:
                return jsonify(ret=-3) #验证码错误
        return jsonify(ret=-4)#手机号格式错误
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/user/changephone', methods = ['POST'])
@auth.login_required
def change_phone():
    '''
    更改用户手机号（帐号）

    URL:/user/changephone
    POST 参数:
        username -- 帐号 (必填)
        code -- 手机验证码 (必填)
    返回值
        {'ret':1,'username':'帐号'} 发送成功
        -1 帐号或密码为空
        -2 帐号已存在
        -3 验证码错误
        -4 手机号格式错误
        -5 系统异常
        -6 帐号更新异常
    '''
    try:
        data = request.get_json()#{\"name\":\"大撒旦撒\"}
        #print data['username'][0]["c"]
        username = data['username']#request.form.get('username','')
        code = data['code']
        #if request.data is not None:
            #username = request.data['username']
            #password = request.data.password

        if len(username)==11:
            if len(username)==0:
                return jsonify(ret=-1) #帐号或密码为空
            if User.isusername(username=username)>0:
                return jsonify(ret=-2) #帐号已存在
            rv = mc.get('code_'+username)
            if rv == code:
                ret = User.updatephone(username)
                if ret==1:
                    return jsonify(ret=1,username=username) #注册成功 ,'token':col1.generate_auth_token(expiration=3600)
                else:
                    return jsonify(ret=-6)
            else:
                return jsonify(ret=-3) #验证码错误
        return jsonify(ret=-4)#手机号格式错误
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/user/update', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def update_user_info():
    '''
    更新个人信息

    URL:/user/update
    POST 参数: 
    	name -- 姓名 (默认 0)
    	sex -- 性别 (默认1,1:男 0:女)
        domainid -- 领域分类id
        industryid -- 行业分类id
    '''
    if request.method == 'POST':
        try: 
            user = User()
            user._id = g.current_user._id
            user.name = request.form.get('name','')
            user.sex = request.form.get('sex',1)
            user.domainid = request.form.get('domainid',1)
            user.industryid = request.form.get('industryid',1)
            user.useredit()
            return jsonify(ret=1) #更新成功
        except Exception,e:
            logging.debug(e)
            return jsonify(ret=-1)#系统异常
@api.route('/user/updateworkexp', methods=['GET','POST'])
#@permission_required(Permission.DISCOVERY)
@auth.login_required
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
    返回值
        {'ret':1} 成功
        0 更新失败
        -1 系统异常
    '''
    if request.method == 'POST':
        try:
            print '0'
            data = request.get_json(force=True)
            #print data+'__________________________'
            print '1'
            _id = g.current_user._id #data['_id']
            print '2_'+str(_id)
            #_id = 73
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
                if len(weitem.name)<65 and len(weitem.job)<41:
                    we.append(weitem)
            user.workexp = we
            state = user.updateworkexp()
            return jsonify(ret=state)
        except Exception,e:
            logging.debug(e)
            return jsonify(ret=-1) #系统异常

@api.route('/user/updateedu', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def update_user_edu():
    '''
    更新教育背景

    URL:/user/updateedu
    POST 参数:
        _id -- 用户ID (测试时使用，上线后删除)
        list -- 工作经历数组 (由多个工作经历字典组成)
            start -- 工作起始时间 (必填，时间戳)
            end -- 工作结束时间 (必填，时间戳)
            name -- 学校名称 (必填)
            dip -- 学历 (必填)
            major -- 专业 (必填)
    '''
    if request.method == 'POST':
        data = request.get_json()

        _list = data['list']
        edu = []
        user = User()
        user._id = g.current_user._id #data['_id']
        for item in _list:
            eduitem1 = Edu()
            eduitem1.start = item['start']
            eduitem1.end = item['end']
            eduitem1.name = item['name']
            eduitem1.dip = item['dip']
            eduitem1.major = item['major']
            if len(eduitem1.name)<65 and len(eduitem1.dip)<41 and len(eduitem1.major)<21:
                edu.append(eduitem1)
        user.edu = edu
        state = user.updateedu()
        return jsonify(ret=state)

@api.route('/appointment/list')
@api.route('/appointment/list/<int:_type>')  # _type=1我约 _type=2被约
@auth.login_required
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
@auth.login_required
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
    #print a_info
    return jsonify(app=a_info.to_json(_type, 0))

@api.route('/user/thinktank', methods=['GET'])
@auth.login_required
def get_user_thinktank():
    '''
    获取用户智囊团列表

    URL:/user/thinktank
    GET 参数: 
        无
    '''
    u_info = User.getinfo(uid=g.current_user._id)
    tt_list = User.getthinktanklist_uid(u_info.thinktank)
    if tt_list is not None:
        return jsonify(list=[item.to_json(5) for item in tt_list])
    else:
        return jsonify(list=[])

@api.route('/user/message', methods=['GET'])
@api.route('/user/message/<int:pageindex>', methods=['GET'])
@auth.login_required
def get_user_message(pageindex=1):
    '''
    获取用户消息列表

    URL:/user/message
        /user/message/<int:pageindex>
    GET 参数:
        pageindex -- 页码 (默认 1)
    '''
    m_list = Message.getlist(uid=g.current_user._id,index=pageindex)
    if m_list is not None:
        return jsonify(list=[item.to_json() for item in m_list])
    else:
        return jsonify(list=[])

@api.route('/user/info')
@auth.login_required
#@permission_required(Permission.DISCOVERY)
def get_user_info():
    '''
    获取用户详细信息

    URL:/user/info
    GET 参数:
        无
    返回值
        info 专家信息
            _id 专家ID
            name 姓名
            sex 性别
            auth 认证
                vip VIP认证
            avaurl 头像地址
            fileurl 介绍图片或视频地址
            geo 坐标
            grade 评级
            intro 简介
            job 职位
            label 标签
            meet_c 见面次数
            edu 教育背景List
                name 学校名称
                start 开始时间
                end 结束时间
                major 专业
                dip 学历
            work 工作经历
                start # 开始时间
                end # 结束时间
                name # 公司名称
                job # 职位
    '''
    u_info = User.getinfo(g.current_user._id)
    return jsonify(info=u_info.to_json())

@api.route('/user/updatetopic', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def update_user_topic():
    '''
    添加话题（专家）

    URL:/user/updatetopic
    POST 参数:
        tid -- 话题id  id大于0为编辑 否则新添加
        title -- 标题
        content -- 内容
        call -- 通话价格
        calltime -- 通话时间
        meet -- 见面价格
        meettime -- 见面时间
    返回值 
        {'ret':1} 成功
        -1 系统异常

    '''
    if request.method == 'POST':

        try:
            data = request.get_json()

            t_info = Topic()
            t_info._id =common.strtoint(data['tid'],0)
            t_info.user_id = g.current_user._id
            t_info.title = data['title']
            #t_info.intro = data['intro']
            t_info.content = data['content']

            tp = TopicPay()
            tp.call = data['call']
            tp.calltime = data['calltime']
            tp.meet = data['meet']
            tp.meettime = data['meettime']
            t_info.pay = tp

            t_info.saveinfo_app()
            return jsonify(ret=1)  #添加成功
        except Exception,e:
            logging.debug(e)
            return jsonify(ret=-1) #系统异常

@api.route('/user/updatepassword', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def update_user_password():
    '''
    更改用户密码

    URL:/user/updatepassword
    POST 参数:
        oldpaw -- 旧密码
        newpaw -- 新密码
    返回值
        {'ret':1} 成功
        0 旧密码验证失败
        -1 系统异常
        -2 旧密码为空
        -3 新密码为空
    '''
    if request.method == 'POST':

        try:
            data = request.get_json()
            oldpaw = data['oldpaw']
            newpaw = data['newpaw']

            if len(oldpaw)<1:
                return jsonify(ret=-2)  #旧密码为空
            if len(newpaw)<1:
                return jsonify(ret=-3)  #新密码为空
            istrue = g.current_user.verify_password(oldpaw)
            if istrue:
                resettoken = g.current_user.generate_reset_token()
                g.current_user.reset_password(resettoken,newpaw)
                return jsonify(ret=1)  #添加成功
            else:
                return jsonify(ret=0)  #旧密码验证失败
        except Exception,e:
            logging.debug(e)
            return jsonify(ret=-1) #系统异常


@api.route('/user/wish', methods=['GET'])
@api.route('/user/wish/<int:pageindex>', methods=['GET'])
@auth.login_required
def get_user_wish(pageindex=1):
    '''
    获取用户心愿单列表

    URL:/user/wish
        /user/wish/<int:pageindex>  
    GET 参数:
        pageindex -- 页码 (默认 1)
    返回值
        list
            _id 用户ID
            name 姓名
            job 职位
            avaurl 头像
            grade 评分
            auth 认证
                vip
            sex 性别

    '''
    #u_info = User.getinfo(uid=94)
    pagesize = 8
    w_list = g.current_user.wish #g.current_user._id
    tcount = len(w_list)
    tpcount = common.getpagecount(tcount,pagesize)
    if pageindex>tpcount:
        pageindex = tpcount
    if pageindex<1:
        pageindex=1
    start =(pageindex-1)*pagesize
    if tcount>0:
        return jsonify(list=[item.to_json(4) for item in User.getwishlist_uid(uidlist=w_list[start:start+pagesize-1])])
    else:
        return jsonify(list=[])


@api.route('/user/updatewish', methods = ['POST'])
@auth.login_required
def update_wish():
    '''
    关注专家
    URL:/user/updatewish
    POST 参数:
        eid -- 专家ID (必填)
        type -- 方式 1添加 0取消
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        data = request.get_json()
        eid = common.strtoint(data['eid'],0)

        _type = data['type']
        if eid>0:
            User.updatewish(g.current_user._id,eid,_type)
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常
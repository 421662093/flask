#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
用户API类
'''

from flask import make_response, request, current_app, url_for
from flask import g,jsonify as flask_jsonify
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from .authentication import auth
from . import api
from .decorators import permission_required
from ..models import Permission, User,WorkExp,Edu, Appointment,Message,collection,Topic,TopicPay,BecomeExpert,SNS,Guestbook,YuntongxunAccount
from ..core.common import jsonify
from ..core import common
from .. import mc
import logging
import json
from ..sdk.yuntongxun import SendTemplateSMS as SMS
import jpush as jpush
from ..sdk.jgpush import pushmessage
from ..sdk.yuntongxun import CreateSubAccount as CSA

@api.route('/user/getcode', methods = ['POST'])
def get_code():
    '''
    验证手机号是否存在，并发送手机验证码

    URL:/user/getcode
    格式
        JSON
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
            smscode = SMS.sendTemplateSMS(username,[code,10],34443)
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
    格式
        JSON
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
    
    data = request.get_json()#{\"name\":\"大撒旦撒\"}
    #print data['username'][0]["c"]
    username = data['username']#request.form.get('username','')
    password = data['password']#request.form.get('password','')
    code = data['code']
    code = common.strtoint(code,-1)
    #if request.data is not None:
        #username = request.data['username']
        #password = request.data.password

    if len(username)==11:
        if len(username)==0 or len(password)==0:
            return jsonify(ret=-1) #帐号或密码为空
        if User.isusername(username=username)>0:
            return jsonify(ret=-2) #帐号已存在
        rv =common.strtoint(mc.get('code_'+username),0)
        if rv == code:
            col1 = User()
            col1._id = collection.get_next_id('users')
            col1.role_id = 3
            col1.username = username
            col1.name = '用户_'+ str(common.getrandom(100000,999999))
            col1.password_hash = password
            col1.state = 1
            if len(username)==11:
                try:
                    ytx = CSA.CreateSubAccount(str(self._id)) #注册容联云子帐号（IM）
                    ytxaccount = YuntongxunAccount()
                    ytxaccount.voipAccount = ytx[0]['voipAccount']
                    ytxaccount.subAccountSid = ytx[1]['subAccountSid']
                    ytxaccount.voipPwd = ytx[2]['voipPwd']
                    ytxaccount.subToken = ytx[3]['subToken']
                    col1.yuntongxunaccount = ytxaccount
                except Exception,e:
                    logging.debug(e)
                    #return jsonify(ret=-5)#系统异常
            col1.saveinfo_app()
            return jsonify(ret=1,username=username) #注册成功 ,'token':col1.generate_auth_token(expiration=3600)
        else:
            return jsonify(ret=-3) #验证码错误
    return jsonify(ret=-4)#手机号格式错误
    

@api.route('/user/changephone', methods = ['POST'])
@auth.login_required
def change_phone():
    '''
    更改用户手机号（帐号）

    URL:/user/changephone
    格式
        JSON
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
        code = common.strtoint(code,-1)
        #if request.data is not None:
            #username = request.data['username']
            #password = request.data.password

        if len(username)==11:
            if len(username)==0:
                return jsonify(ret=-1) #帐号或密码为空
            if User.isusername(username=username)>0:
                return jsonify(ret=-2) #帐号已存在
            rv = common.strtoint(mc.get('code_'+username),0)
            if rv == code:
                ret = User.updatephone(g.current_user.role_id,username)
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
    格式
        JSON
    POST 参数: 
    	name -- 姓名 (默认 0)
    	sex -- 性别 (默认1,1:男 0:女)
        domainid -- 领域分类id
        industryid -- 行业分类id
        isava -- 是否更新头像 1是 0否
    '''
    if request.method == 'POST':
        try: 
            data = request.get_json()
            user = User()
            user._id = g.current_user._id
            user.name = data['name']
            user.role_id = g.current_user.role_id
            user.sex = common.strtoint(data['sex'],1)
            isava = common.strtoint(data['isava'],0)
            if isava==1:
                user.avaurl = 'http://kdzj2015-10001870.image.myqcloud.com/kdzj2015-10001870/0/avatar_'+str(user._id)+'/original?random='+str(common.getstamp())
            if user.role_id==2:
                user.domainid = common.strtoint(data['domainid'],0)
                user.industryid = common.strtoint(data['industryid'],0)
            user.useredit()
            return jsonify(ret=1) #更新成功
        except Exception,e:
            logging.debug(e)
            return jsonify(ret=-1)#系统异常

@api.route('/user/updateemail', methods=['POST'])
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def update_user_email():
    '''
    更新邮箱

    URL:/user/updateemail
    格式
        JSON
    POST 参数: 
        email -- 邮箱
    返回值
        {'ret':1} 成功
        0 更新失败
        -1 系统异常
    '''
    if request.method == 'POST':
        try: 
            data = request.get_json()
            email = data['email']
            User.updateemail(g.current_user._id,email)
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
    格式
        JSON
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
            data = request.get_json()
            #print data+'__________________________'
            _id = g.current_user._id #data['_id']
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
    格式
        JSON
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
    格式
        JSON
    GET 参数: 
        _type -- 预约类型 (1:我约 2:被约) 
    '''

    a_list = Appointment.getlist(_type=_type, appid=g.current_user._id)
    return jsonify(list=[item.to_json(uid=_type) for item in a_list])


@api.route('/appointment/info/<int:aid>')
#@api.route('/appointment/info/<int:aid>/<int:_type>')  # _type=1我约 _type=2被约
@auth.login_required
#@permission_required(Permission.DISCOVERY)
def get_appointment_info(aid):#,_type=1
    '''
    获取用户预约详情

    URL:
        /appointment/info/<int:aid>
    格式
        JSON
    GET 参数: 
        aid -- 预约ID (默认 0)
    '''

    a_info = Appointment.getinfo(aid=aid)
    if a_info is not None:
        return jsonify(app=a_info.to_json(uid=g.current_user._id, type=0))
    else:
        return jsonify(app={})

@api.route('/user/addappointment', methods=['POST'])
@auth.login_required
def add_user_appointment():
    '''
    提交预约订单（用户）

    URL:
        /user/addappointment
    格式
        JSON
    POST 参数:
        aid -- 预约ID
        tid -- 话题ID
        at -- 预约方式  1通话 2见面
        appdate -- 预约时间
        address -- 地址
        remark -- 备注
    返回值
        {'ret':1} 成功
        -1 认证失败，无法创建订单
    '''

    data = request.get_json()
    aid = common.strtoint(data['aid'],0)
    tid = common.strtoint(data['tid'],0)
    at = common.strtoint(data['at'],1)
    temppri = 0
    t_info = Topic.getinfo(tid)
    if t_info is not None and aid is t_info.user_id:
        app = Appointment()
        app.user_id = g.current_user._id
        app.appid = aid
        app.topic_title = t_info.title
        app.topic_id = tid
        app.appdate = common.strtoint(data['appdate'],0)
        app.apptype = common.strtoint(data['at'],1)
        app.address = data['address']

        if app.apptype==1:
            app.price = t_info.pay.call
        elif app.apptype==2:
            app.price = t_info.pay.meet

        app.attachment = []
        #app.remark = data['remark']
        app.state = 1
        app.paystate = 0
        nowid = app.editinfo()

        msg = Message()
        msg.user_id = app.appid
        msg.appointment_id = nowid
        msg.type = 4
        msg.title = '预约消息'
        msg.content = '您有一个新的预约订单请您查看。'
        msg.saveinfo()
        pushmessage(jpush,'您有一个新的预约订单请您查看。',{'type':'viewapp','app_id':str(nowid),'apptype':2},[app.appid])
        return jsonify(ret=nowid)  #创建订单成功
    return jsonify(ret=-1)  #认证失败，无法创建订单

@api.route('/user/thinktank', methods=['GET'])
@auth.login_required
def get_user_thinktank():
    '''
    获取用户智囊团列表

    URL:/user/thinktank
    格式
        JSON
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
    格式
        JSON
    GET 参数:
        pageindex -- 页码 (默认 1)
    返回值 
        _id -- 消息ID
        title -- 标题
        content -- 内容
        appointment_id -- 预约订单ID
        date -- 创建时间
        type -- 消息类型 1预约成功 2预约失败 3温馨提醒 4消息提醒
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
    格式
        JSON
    返回值
        info 专家信息
            _id 专家ID
            name 姓名
            sex 性别
            auth 认证
                expertprocess 认证专家流程  0未认证 1-5
                becomeexpert 成为专家 1已提交 0未提交
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
            money 账户余额
            apptime 预约时间（专家可预约时间）
            calltime 通话时间 (分享可获得)
            wish 心愿单 数组[用户id,用户id]
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


@api.route('/user/updateocp', methods = ['POST'])
@auth.login_required
def update_ocp():
    '''
    认证专家
    URL:/user/updateocp
    POST 参数:
        type -- 类型 (必填) 0成为专家 1个人简介  2个人标签 3工作经历 4教育背景
        type=0
            name 姓名
            #industry 行业
            #company 公司
            #job 职位
            phone 手机
            weixin 微信号
            qq QQ
        type=1
            intro 简介
        type=2
            label 数组[字符串1,字符串2]
        type=3 workexp 数组[字典1，字典2]
            name 姓名
            start 开始时间 时间戳
            end 结束时间 时间戳
            job 职业
        type=4 edu 数组[字典1，字典2]
            name 姓名
            start 开始时间 时间戳
            end 结束时间 时间戳
            dip 学历
            major 专业
    返回值
        {'ret':1} 成功
        -1 type=0 已提交
        -5 系统异常
    '''
    try:
        data = request.get_json()
        _type = common.strtoint(data['type'],0)
        if _type>0:
            user = User()
            user._id = g.current_user._id
            if _type==1:
                user.intro = data['intro']
            elif _type==2:
                user.label = common.delrepeat(data['label'])
            elif _type==3:
                welist= []
                tempwe = data['workexp']
                for item in tempwe:
                    tempWorkExp = WorkExp()
                    tempWorkExp.name = item['name']
                    if len(tempWorkExp.name)>0:
                        tempWorkExp.start = item['start']
                        tempWorkExp.end = item['end']
                        tempWorkExp.job = item['job']
                    welist.append(tempWorkExp)
                user.workexp = welist
            elif _type==4:
                edulist= []
                tempedu = data['edu']
                for item in tempedu:
                    tempedu = Edu()
                    tempedu.name = item['name']
                    if len(tempedu.name)>0:
                        tempedu.start = item['start']
                        tempedu.end = item['end']
                        tempedu.dip = item['dip']
                        tempedu.major = item['major']
                        edulist.append(tempedu)
                user.edu = edulist
            user.updateocp(_type)
        elif _type==0:
            if g.current_user.auth.becomeexpert==0:
                be = BecomeExpert()
                be.user_id = g.current_user._id
                be.name=data['name']
                #be.industry=data['industry']
                #be.company=data['company']
                #be.job=data['job']
                be.phone=data['phone']
                be.weixin=data['weixin']
                be.qq=data['qq']
                be.saveinfo()
            else:
                return jsonify(ret=-1)#已提交
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常


@api.route('/user/updateshare', methods = ['POST'])
@auth.login_required
def update_share():
    '''
    关注专家
    URL:/user/updateshare
    POST 参数:
        type -- 分享途径 1微信 2朋友圈 3QQ 4新浪
    返回值
        {'ret':1} 成功
        -1 今天已分享
        -5 系统异常
    '''
    try:
        data = request.get_json()
        _type = common.strtoint(data['type'],0)
        nowtime = common.getdaystamp()

        if _type==1 and g.current_user.stats.wxshare==nowtime:
            return jsonify(ret=-1)
        elif _type==2 and g.current_user.stats.pyshare==nowtime:
           return jsonify(ret=-1)
        elif _type==3 and g.current_user.stats.qqshare==nowtime:
            return jsonify(ret=-1)
        elif _type==4 and g.current_user.stats.sinashare==nowtime:
            return jsonify(ret=-1)

        User.updateshare(g.current_user._id,_type)
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/user/snslogin', methods = ['POST'])
def user_snslogin():
    '''
    第三方登录
    URL:/user/snslogin
    POST 参数:
        sns -- 第三方平台 1新浪 2QQ 3微信
        uid -- 第三方UID
        username -- 第三方昵称
        token -- 第三方token
        avaurl -- 头像
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        data = request.get_json()
        sns = common.strtoint(data['sns'],0)
        uid = data['uid']
        name = data['username']
        token = data['token']
        avaurl = data['avaurl']
        if sns>0:
            user = User.snslogin(sns,uid)
            if user is not None:
                user = User.objects(_id=user._id).first()
                login_user(user, True)
            else:
                col1 = User()
                col1.role_id = 3

                col1.name = name
                col1.password = ''
                col1.avaurl = avaurl
                sn = SNS()
                sn.token = token
                if sns==1:
                    sn.sina = uid
                    col1.username = '-1'
                elif sns==2:
                    sn.qq = uid
                    col1.username = '-2'
                elif sns==3:
                    sn.weixin = uid
                    col1.username = '-3'
                col1.sns = sn
                col1.saveinfo()
                user = User.snslogin(sns,uid)
                #user = User.objects(_id=user._id).first()
                login_user(user, True)
            return flask_jsonify({'token': user.generate_auth_token(expiration=2592000), 'expiration': 2592000,'_id': user._id})
        #return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/user/addguestbook', methods = ['POST'])
@auth.login_required
def add_guestbook():
    '''
    添加留言反馈
    URL:/user/addguestbook
    POST 参数:
        content -- 反馈内容
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        data = request.get_json()
        gb = Guestbook()
        gb.user_id = g.current_user._id
        gb.content = data['content']
        gb.saveinfo()
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/guest/addguestbook', methods = ['POST'])
#@auth.login_required
def add_guest_guestbook():
    '''
    添加留言反馈
    URL:/user/addguestbook
    POST 参数:
        content -- 反馈内容
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        data = request.get_json()
        gb = Guestbook()
        gb.content = data['content']
        gb.saveinfo()
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常




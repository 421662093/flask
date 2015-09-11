#!/usr/bin/env python
#-*- coding: utf-8 -*-
#专家API类

from flask import request, current_app, url_for
from flask import g
from .authentication import auth
from . import api
from .decorators import permission_required
from ..models import Permission, User, Topic, Comment,Appointment
from ..core.common import jsonify
from ..core import common
import logging
from ..sdk.jgpush import pushmessage
import jpush as jpush
#from .. import searchwhoosh
# from ..models import discovery


@api.route('/expert/map/<float:x>/<float:y>')
#@permission_required(Permission.DISCOVERY)
def get_expert_map(x=0, y=0):
    '''
    获取附近专家(地图)

    URL:/expert/map/<float:x>/<float:y>
    GET 参数: 
        x -- 经度 (必填) 
        y -- 纬度 (必填) 
    '''
    pagesize = 10
    if x == 0:
        u_list = User.getlist_app(count=pagesize)
    else:
        u_list = User.getlist_geo_map(x,y,count=pagesize)

    return jsonify(list=[item.to_json(6) for item in u_list])

@api.route('/expert/list/<int:ind>/<int:index>')
@api.route('/expert/list/<float:x>/<float:y>')
@api.route('/expert/list/<float:x>/<float:y>/<int:ind>')
@api.route('/expert/list/<float:x>/<float:y>/<int:ind>/<int:index>')
#@permission_required(Permission.DISCOVERY)
def get_expert_list(x=0.0, y=0.0,ind=0,index=1):
    '''
    获取附近专家(列表)

    URL:/expert/list/<int:ind>/<int:index>
        /expert/map/<float:x>/<float:y>
        /expert/map/<float:x>/<float:y>/<int:ind>
        /expert/list/<float:x>/<float:y>/<int:ind>/<int:index>
    GET 参数: 
        x -- 经度 (选填) 为0.0则 按照默认排序 否则 按照附近检索
        y -- 纬度 (选填) 
        ind -- 行业ID (选填 默认 0) 
        index -- 页码 (选填 默认 1) 
    '''
    pagesize = 10
    if x == 0:
        u_list = User.getexpertlist_app(industryid=ind,index=index,count=pagesize)
    else:
        u_list = User.getlist_geo_list(x,y,industryid=ind,count=pagesize)

    return jsonify(list=[item.to_json(6) for item in u_list])

@api.route('/expert/info/<int:uid>')
#@permission_required(Permission.DISCOVERY)
def get_expert_info(uid):
    '''
    获取专家详细信息

    URL:/expert/info/<int:uid>
    GET 参数:
        uid -- 专家ID (必填)
    返回值
    expert
        info 专家信息
            _id 专家ID
            name 姓名
            sex 性别
            auth 认证
                expertprocess 认证专家流程  0未认证 1-4
                expert 认证专家 1已认证 0未认证
            bgurl 顶部背景图片
            avaurl 头像地址
            fileurl 介绍图片或视频地址
            geo 坐标
            grade 评级
            intro 简介
            content 详细介绍
            job 职位
            label 标签
            meet_c 见面次数
            follow 第三方List
                name 名称
                url 地址
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
        comment
        topic
    '''
    u_info = User.getinfo(uid)
    t_list = Topic.getlist(uid=uid, count=3)
    c_list = Comment.getlist(uid=uid, page=1, count=2)
    return jsonify(expert={
        'info': u_info.to_json(-1),
        'topic': [item.to_json() for item in t_list],
        'comment': [item.to_json() for item in c_list]
    })


@api.route('/topic/info/<int:tid>')
#@permission_required(Permission.DISCOVERY)
def get_topic_info(tid):
    '''
    获取话题详细信息

    URL:/topic/info/<int:tid>
    GET 参数: 
        tid -- 话题ID (必填) 
    '''
    t_info = Topic.getinfo(tid)
    c_count = Comment.getcount(tid)
    return jsonify(topic={
        '_id': t_info.id,
        'user_id': t_info.user_id,
        'title': t_info.title.encode('utf-8'),
        'con': t_info.content.encode('utf-8'),
        'pay': t_info.pay.to_json(),  # self.auth.vip
        'date': t_info.date,
        'grade': t_info.grade,
        'avaurl': common.getavatar(userid=t_info.id),
        'comment_count':c_count
    })


@api.route('/comment/list/<int:uid>')
@api.route('/comment/list/<int:uid>/<int:page>')
#@permission_required(Permission.DISCOVERY)
def get_comment_list(uid, page=1):
    '''
    获取专家评论列表

    URL:/comment/info/<int:uid>
        /comment/list/<int:uid>/<int:page>
    GET 参数: 
        uid -- 专家ID (必填) 
        page -- 页码 (选填 默认 1) 
    '''
    c_list = Comment.getlist(uid=uid, page=page, count=10)
    return jsonify(list=[item.to_json() for item in c_list])

@api.route('/expert/firstsearch')
#@permission_required(Permission.DISCOVERY)
def get_expertsearch_first_list():
    '''
    快速检索专家列表

    URL:/expert/firstsearch
    GET 参数:
        text -- 检索关键词 (必填)
    '''
    #智能提示，检索
    #query  =  {'$or':[{'col1':{'$regex':srch_text}},{'col2':{'$regex':srch_text}},{'col3':{'$regex':srch_text}}]}
    text = request.args.get('text','')
    if len(text)>0:
        text = common.htmlescape(text)
        #srch_text = '^('+text+').*'
        #query  =  {'$or':[{'name':{'$regex':srch_text}},{'job':{'$regex':srch_text}}]}
        #elist = User.objects(__raw__=(query)).only('name','_id')
        elist= []
        tmp = []
        tmptext= ''
        for item in User.search(text):
            tmptext = cmp(item.name,text)==1 and item.name or item.job
            if tmptext not in tmp:
                tmp.append(tmptext)
                elist.append({
                    'name': tmptext.encode('utf-8')
                })
        return jsonify(list=elist)
    else:
        return []

@api.route('/expert/search')
#@permission_required(Permission.DISCOVERY)
def get_expertsearch_list():
    '''
    全文检索专家列表

    URL:/expert/search
    GET 参数:
        text -- 检索关键词 (必填 检索字段name,job,label) 
    '''
    #全文检索，搜索界面
    text = request.args.get('text','')
    #content = request.form.get('content','')
    #text = text.translate('<')
    text = common.htmlescape(text)
    #ret = searchwhoosh.search(text,1)
    ret = User.Q_YUNSOU(text)
    if ret is not None:
        eid = []
        eidlen = ret['data']['eresult_num']
        if eidlen>0:
            for eitem in ret['data']['result_list']:
                eid.append(eitem['doc_id'])
            elist=[item.to_json(5) for item in User.getlist_uid_app(uidlist=eid, count=10)]
        else:
            elist=[]
        return jsonify(list=elist)
    else:
        return jsonify(list=[])

@api.route('/expert/inv')
@api.route('/expert/inv/<int:index>')
#@permission_required(Permission.DISCOVERY)
@auth.login_required
def get_expertinv_list(index=1):
    '''
    专家清单
    URL:/expert/inv
        /expert/inv/<int:index>
    GET 参数:
        index -- 页码(默认1)
    返回值
        _id 清单id
        title 标题
        content 内容
        price 价格
        unit 单位
        sort 排序
    '''
    i_list = ExpertInv.getlist(uid=g.current_user._id, index=index)
    return jsonify(list=[item.to_json() for item in i_list])

@api.route('/expert/updateinv')
@auth.login_required
def update_expert_inv():
    '''
    更新专家清单
    URL:/expert/updateinv
    POST 参数:
        eid 清单id  id大于0为编辑 否则新添加
        title 标题
        content 内容
        price 价格
        unit 单位
        #sort 排序
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    if request.method == 'POST':
        try:
            einv = ExpertInv()
            data = request.get_json(force=True)
            einv._id = common.strtoint(data['eid'],0)
            einv.user_id = g.current_user._id
            einv.title = data['title']
            einv.content = data['content']
            einv.price = data['price']
            einv.unit = data['unit']
            einv.saveinfo()
            return jsonify(ret=1)
        except Exception,e:
            logging.debug(e)
            return jsonify(ret=-5) #系统异常

@api.route('/user/updateintro', methods = ['POST'])
@auth.login_required
def update_user_intro():
    '''
    更新简介
    URL:/user/updateintro
    POST 参数:
        label -- 标签 字符串数组
        fileurl -- 上传文件url
        intro -- 简介
        content -- 内容
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        user = User()
        data = request.get_json()
        user._id = g.current_user._id
        user.fileurl = data['fileurl']
        user.intro = data['intro']
        user.content = data['content']
        user.label = common.strtoint(data['label'],[])
        user.label = common.delrepeat(user.label) #移除标签中重复
        user.updateintro()
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/expert/updateapptime', methods = ['POST'])
@auth.login_required
def update_expert_apptime():
    '''
    更新专家可预约时间
    URL:/expert/updateapptime
    POST 参数:
        apptime -- 预约时间数组[时间戳1,时间戳2]
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        data = request.get_json()
        apptime = data['apptime']
        User.updateapptime(g.current_user._id,apptime)
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常

@api.route('/expert/updateapptype', methods = ['POST'])
@auth.login_required
def update_expert_apptype():
    '''
    更新专家预约模式
    URL:/expert/updateapptime
    POST 参数:
        call -- 通话模式 1开启 0关闭
        meet -- 见面模式 1开启 0关闭
    返回值
        {'ret':1} 成功
        -5 系统异常
    '''
    try:
        data = request.get_json()
        call = common.strtoint(data['call'],0)
        meet = common.strtoint(data['meet'],0)
        apptype = 0
        if call==1 and meet==1:
            apptype=0x01 | 0x02
        elif call==1:
            apptype=0x01
        elif meet==1:
            apptype=0x02
        User.updateapptype(g.current_user._id,apptype)
        return jsonify(ret=1)#添加成功
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常


@api.route('/expert/updateappstate', methods = ['POST'])
@auth.login_required
def update_expert_appstate():
    '''
    更新订单状态（专家）
    URL:/expert/updateappstate
    POST 参数:
        appid -- 订单id
        state -- 状态状态 0拒绝接单 2确认接单 4已完成
        time -- 见面时间(分钟) 当state为4时有效
    返回值
        {'ret':1} 成功
        -1 订单状态改变失败
        -5 系统异常
    '''
    try:
        data = request.get_json()
        appid = common.strtoint(data['appid'],0)
        state = common.strtoint(data['state'],-1)
        time = common.strtoint(data['time'],0)
        if appid>0 and (state==0 or state==2 or state==4):
            Appointment.updateappstate(uid=g.current_user._id,aid=appid,state=state,time=time)
            a_info = Appointment.getinfo(appid)
            if a_info is not None:
                if state==0:
                    pushmessage(jpush,'口袋专家订单已被拒绝',{'type':'update_appointment','app_id':appid,'state':0},[a_info.user_id])
                elif state==2:
                    pushmessage(jpush,'口袋专家订单已确认',{'type':'update_appointment','app_id':appid,'state':2},[a_info.user_id])
                elif state==4:
                    pushmessage(jpush,'口袋专家订单已完成',{'type':'update_appointment','app_id':appid,'state':4},[a_info.user_id])
            return jsonify(ret=1)
        else:
            return jsonify(ret=-1)#订单确认失败
    except Exception,e:
        logging.debug(e)
        return jsonify(ret=-5)#系统异常
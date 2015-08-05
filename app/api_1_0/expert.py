#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import request, current_app, url_for
from . import api
from .decorators import permission_required
from ..models import Permission, User, Topic, Comment
from ..core.common import jsonify
from ..core import common
from .. import searchwhoosh
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
        u_list = User.getlist(count=pagesize)
    else:
        u_list = User.getlist_geo_map(x,y,count=pagesize)

    return jsonify(list=[item.to_json(6) for item in u_list])

@api.route('/expert/list/<float:x>/<float:y>')
@api.route('/expert/list/<float:x>/<float:y>/<int:ind>')
#@permission_required(Permission.DISCOVERY)
def get_expert_list(x=0, y=0,ind=0):
    '''
    获取附近专家(列表)

    URL:/expert/map/<float:x>/<float:y>
        /expert/map/<float:x>/<float:y>/<int:ind>
    GET 参数: 
        x -- 经度 (必填) 
        y -- 纬度 (必填) 
        ind -- 行业ID (选填 默认 0) 
    '''
    pagesize = 10
    if x == 0:
        u_list = User.getlist(count=pagesize)
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
    '''
    u_info = User.getinfo(uid)
    t_list = Topic.getlist(uid=uid, count=2)
    c_list = Comment.getlist(uid=uid, page=1, count=2)
    return jsonify(expert={
        'info': u_info.to_json(),
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
    return jsonify(topic={
        '_id': t_info.id,
        'user_id': t_info.user_id,
        'title': t_info.title.encode('utf-8'),
        'con': t_info.content.encode('utf-8'),
        'pay': t_info.pay.to_json(),  # self.auth.vip
        'date': t_info.date,
        'grade': t_info.grade,
        'avaurl': common.getavatar(userid=t_info.id)
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
    ret = searchwhoosh.search(text,1)
    eid = []
    eidlen = len(ret['results'])
    print eidlen
    if eidlen>0:
        for eitem in ret['results']:
            eid.append(eitem['eid'])
        elist=[item.to_json(5) for item in User.getlist_uid(uidlist=eid, count=10)]
    else:
        elist=[]
    return jsonify(list=elist)
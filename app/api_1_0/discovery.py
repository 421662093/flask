#!/usr/bin/env python
#-*- coding: utf-8 -*-
#发现API类

from flask import make_response, request, current_app, url_for
from . import api
from .decorators import permission_required
from ..models import Permission, Inventory, Topic, Ad, User
from ..core.common import jsonify
from ..core import common
# from ..models import discovery


@api.route('/discovery/list')
#@permission_required(Permission.DISCOVERY)
def get_discovery_list():
    '''
    获取发现首页信息

    URL:/discovery/list
    GET 参数: 
        无
    '''
    i_list = Ad.getlist(count=6)
    tt_list = Topic.getlist(uid=0, count=2)
    t_list = Topic.getlist(uid=11, count=2)
    return jsonify(discovery={
        'ad': [item.to_json() for item in i_list],
        'topic_team': [item.to_json(1) for item in tt_list],
        'topic': [item.to_json(2) for item in t_list],
    })


@api.route('/discovery/inventory/<int:id>')
#@permission_required(Permission.DISCOVERY)
def get_discovery_Inventory(id):
    '''
    获取清单信息

    URL:/discovery/inventory/<int:id>
    GET 参数: 
        id -- 清单ID (必填) 
    '''
    #获取清单信息
    i_info = Inventory.getinfo(iid=id)
    return jsonify(inv=i_info.to_json())

@api.route('/discovery/inventory/<int:iid>/<int:tid>')
#@permission_required(Permission.DISCOVERY)
def get_discovery_Inventory_Expert(iid,tid):
    '''
    获取清单话题专家列表

    URL:/discovery/inventory/<int:iid>/<int:tid>
    GET 参数: 
        iid -- 清单ID (必填) 
        tid -- 话题ID (必填) 
    '''
    #
    ie=[]
    i_info = Inventory.getinfo(iid=iid)
    if i_info is not None:
        for item in i_info.topic:
            if(item._id==tid):
                ie=item.expert
    #i_info = Inventory.getexpertlist(iid=iid,tid=tid)
    return jsonify(Expert=[item.to_json(4) for item in User.getlist_uid(uidlist=ie)])

@api.route('/discovery/topicteam/<int:tid>')
#@permission_required(Permission.DISCOVERY)
def get_discovery_TopicTeam(tid):
    '''
    获取专家团详情信息

    URL:/discovery/topicteam/<int:tid>
    GET 参数: 
        tid -- 话题ID (必填) 
    '''
    t_info = Topic.getinfo(tid)
    return jsonify(TopicTeam=t_info.to_json(3))

@api.route('/discovery/topicteam/expert/<int:tid>')
#@permission_required(Permission.DISCOVERY)
def get_discovery_ExpertTeam(tid):
    '''
    获取专家团专家列表

    URL:/discovery/topicteam/expert/<int:tid>
    GET 参数: 
        tid -- 话题ID (必填) 
    '''
    t_info = Topic.getinfo_expert(tid)
    if len(t_info.expert) > 0:
        return jsonify(Expert=[item.to_json(4) for item in User.getlist_uid(uidlist=t_info.expert)])
    else:
        return jsonify(Expert=[])

#!/usr/bin/env python
#-*- coding: utf-8 -*-
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
    #获取清单信息
    i_info = Inventory.getinfo(iid=id)
    return jsonify(inv=i_info.to_json())

@api.route('/discovery/inventory/<int:iid>/<int:tid>')
#@permission_required(Permission.DISCOVERY)
def get_discovery_Inventory_Expert(iid,tid):
    #获取清单话题专家列表
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
def get_discovery_TopicTeam(tid):  # 专家团详情页面
    t_info = Topic.getinfo(tid)
    return jsonify(TopicTeam=t_info.to_json(3))

@api.route('/discovery/topicteam/expert/<int:tid>')
#@permission_required(Permission.DISCOVERY)
def get_discovery_ExpertTeam(tid):  # 专家团，获取专家列表
    t_info = Topic.getinfo_expert(tid)
    if len(t_info.expert) > 0:
        return jsonify(Expert=[item.to_json(4) for item in User.getlist_uid(uidlist=t_info.expert)])
    else:
        return jsonify(Expert=[])

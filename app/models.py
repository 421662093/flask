#!/usr/bin/env python
#-*- coding: utf-8 -*-
from datetime import datetime
from mongoengine import EmbeddedDocument, EmbeddedDocumentField,Q
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
import hashlib

'''
from markdown import markdown
import bleach  # html 清除工具
'''
from app.exceptions import ValidationError
from flask import current_app, request, url_for
from flask.ext.login import UserMixin, AnonymousUserMixin
from . import db,mc,conf,q_search, login_manager#,searchwhoosh
from core import common
import json
import logging
#import cpickle as pickle

Q_SOUYUN_ACTION = 'DataManipulation' #添加操作 云搜
Q_SOUYUN_SEARCH = 'DataSearch' #搜索操作 云搜

class Permission:
    VIEW = 0x01 # 查看
    EDIT = 0x02 # 编辑
    DELETE = 0x04 # 删除
    ADMINISTER = 0x80

class RolePermissions(db.EmbeddedDocument):  # 角色权限
    user = db.IntField(default=0, db_field='u') #用户
    topic = db.IntField(default=0, db_field='t') #话题
    inventory = db.IntField(default=0, db_field='i') #清单
    appointment = db.IntField(default=0, db_field='a') #预约
    ad = db.IntField(default=0, db_field='ad') #广告
    role = db.IntField(default=0, db_field='r') #角色
    log = db.IntField(default=0, db_field='l') #日志
    expertauth = db.IntField(default=0, db_field='ea') #审核专家

    def to_json(self):
        json_rp = {
            'user': self.user,
            'topic': self.topic,
            'inventory': self.inventory,
            'appointment': self.appointment,
            'ad': self.ad,
            'role': self.role,
            'log': self.log,
            'expertauth': self.expertauth
        }
        return json_rp

class Role(db.Document):
    __tablename__ = 'roles'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    name = db.StringField(max_length=64, required=True,db_field='n')
    default = db.BooleanField(default=False, db_field='d')
    permissions = db.EmbeddedDocumentField(
        RolePermissions, default=RolePermissions(), db_field='p')  # 统计
    CACHEKEY = {
        'list':'rolelist',
        'item':'roleitem'
    }
    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.VIEW | Permission.EDIT | Permission.DELETE | Permission.ADMINISTER, True),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role()
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            role._id = collection.get_next_id('role')
            role.name = '12@qq.com'
            role.save()
    @staticmethod
    def getlist():
            rv = mc.get(Role.CACHEKEY['list'])
            # rv = rs.get(Role.CACHEKEY['list'])
            if rv is None:
                rv = Role.objects().limit(30)
                temp =  json.dumps([item.to_json() for item in rv])
                try:
                    mc.set(Role.CACHEKEY['list'],temp)
                except Exception,e:
                    logging.debug(e)
                    return rv
                #rs.set(Role.CACHEKEY['list'],temp)
            else:
                rv = json.loads(rv)
            return rv #Role.objects().limit(30)

    def editinfo(self):
        mc.delete(Role.CACHEKEY['list'])
        if self._id > 0:
            update = {}
            # update.append({'set__email': self.email})

            if len(self.name) > 0:
                update['set__name'] = self.name
            update['set__default'] = self.default
            update['set__permissions'] = self.permissions
            Role.objects(_id=self._id).update_one(**update)
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            return self._id

    @staticmethod
    def getinfo(rid):
        #获取指定id 角色信息
        #return Role.objects(_id=rid).first()
        #'''
        if rid>0:
            rlist = Role.getlist()
            for item in rlist:
                if item['_id']==rid:
                    return item
            return None
        else:
            return None
        #'''
    def to_json(self):
        json_role = {
            '_id': self.id,
            'name': self.name.encode('utf-8'),
            'default': self.default,
            'permissions': self.permissions.to_json()
        }
        return json_role
    '''
    def __repr__(self):
        return '<Role %r>' % self.name # 角色权限
    '''

class UserStats(db.EmbeddedDocument):  # 会员统计
    meet = db.IntField(default=0, db_field='m') #见面次数
    comment_count = db.IntField(default=0, db_field='cc')  # 评论人数
    comment_total = db.IntField(default=0, db_field='ct')  # 评论总分
    lastaction = db.IntField(default=0, db_field='la')  # 最后更新时间
    rand = db.IntField(default=common.getrandom(), db_field='r')  # 随机数 用于随机获取专家列表
    message_count = 0  # 消息个数
    oldx = db.IntField(default=0, db_field='x')  # 旧字段 无效

    baidu = db.IntField(default=0, db_field='b')  # 百度关注数
    weixin = db.IntField(default=0, db_field='w')  # 微信关注数
    zhihu = db.IntField(default=0, db_field='z')  # 知乎关注数
    sina = db.IntField(default=0, db_field='s')  # 新浪关注数
    twitter = db.IntField(default=0, db_field='t')  # 推特关注数
    facebook = db.IntField(default=0, db_field='f')  # 脸谱关注数
    github = db.IntField(default=0, db_field='g')  # GIT关注数

    baiduurl = db.StringField(default='', db_field='bu')  # 百度地址
    weixinurl = db.StringField(default='', db_field='wu')  # 微信地址
    zhihuurl = db.StringField(default='', db_field='zu')  # 知乎地址
    sinaurl = db.StringField(default='', db_field='su')  # 新浪地址
    twitterurl = db.StringField(default='', db_field='tu')  # 推特地址
    facebookurl = db.StringField(default='', db_field='fu')  # 脸谱地址
    githuburl = db.StringField(default='', db_field='gu')  # GIT地址

    wxshare = db.IntField(default=0, db_field='ws')  # 微信分享 分享后记录当天时间戳，一天可分享一次
    pyshare = db.IntField(default=0, db_field='ps')  # 朋友圈分享 分享后记录当天时间戳，一天可分享一次
    qqshare = db.IntField(default=0, db_field='qs')  # QQ地址 分享后记录当天时间戳，一天可分享一次
    sinashare = db.IntField(default=0, db_field='ss')  # 新浪分享 分享后记录当天时间戳，一天可分享一次

    def to_json(self):
        json_us = {
            'meet': self.meet
        }
        return json_us

class YuntongxunAccount(db.EmbeddedDocument):  # 容联云子帐号
    voipAccount = db.StringField(default='', db_field='va')
    subAccountSid = db.StringField(default='', db_field='sa')
    voipPwd = db.StringField(default='', db_field='vp')
    subToken = db.StringField(default='', db_field='st')

class UserOpenPlatform(db.EmbeddedDocument):  # 开放平台
    name = db.StringField(default='', db_field='n')  # 名称
    url = db.StringField(default='', db_field='u')  # 地址

    def to_json(self):
        json = {
            'name': self.name,
            'url':self.url
        }
        return json

class WorkExp(db.EmbeddedDocument):  # 工作经历
    start = db.IntField(default=common.getstamp(),  db_field='s')  # 开始时间
    end = db.IntField(default=common.getstamp(), db_field='e')  # 结束时间
    name = db.StringField(default='',max_length=64, db_field='n')  # 公司名称
    job = db.StringField(default='',max_length=40, db_field='j')  # 职位
    intro = db.StringField(db_field='i')  # 简介 暂停使用

    def to_json(self):
        json_we = {
            'start': self.start,
            'end': self.end,
            'name': self.name.encode('utf-8'),
            'job': self.job.encode('utf-8'),
            #'intro': self.intro.encode('utf-8')
        }
        return json_we


class Edu(db.EmbeddedDocument):  # 教育背景
    start = db.IntField(default=common.getstamp(),  db_field='s')  # 开始时间
    end = db.IntField(default=common.getstamp(),  db_field='e')  # 结束时间
    name = db.StringField(default='',max_length=64, db_field='n')  # 学校名称
    dip = db.StringField(default='', max_length=40, db_field='d')  # 文凭
    major = db.StringField(default='',max_length=20, db_field='m')  # 专业

    def to_json(self):
        json_edu = {
            'start': self.start,
            'end': self.end,
            'name': self.name.encode('utf-8'),
            'dip': self.dip.encode('utf-8'),
            'major': self.major.encode('utf-8')
        }
        return json_edu

class UserAuth(db.EmbeddedDocument):  # 认证信息
    expertprocess = db.IntField(default=0,  db_field='ep')  #认证专家流程  0未认证 1-5
    expert = db.IntField(default=0,  db_field='e')  #认证专家 1已认证 0未认证
    becomeexpert = db.IntField(default=0,  db_field='be')  #成为专家 1已提交 0未提交
    def to_json(self):
        json = {
            'expertprocess': self.expertprocess,
            'expert':self.expert,
            'becomeexpert':self.becomeexpert
        }
        return json

class SNS(db.EmbeddedDocument):  # 第三方社交登录
    sina = db.StringField(default='', db_field='s') 
    qq = db.StringField(default='',  db_field='q') 
    weixin = db.StringField(default='', db_field='w') 
    token = db.StringField(default='',  db_field='t')  #token

class User(UserMixin, db.Document):  # 会员
    __tablename__ = 'users'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    email = db.StringField(default='', max_length=64, db_field='e')  # 邮箱
    weixin = db.StringField(default='', max_length=64, db_field='wx')  # 微信
    qq = db.StringField(default='', max_length=10, db_field='qq')  # QQ
    name = db.StringField(
        default='', max_length=64, required=True, db_field='n')  # 姓名
    username = db.StringField(
        default='', max_length=64, required=True, db_field='un')  # 帐号
    password_hash = db.StringField(
        default='', required=True, max_length=128, db_field='p')  # 密码
    confirmed = db.IntField(default=1, db_field='c')  # 是否允许访问api
    role_id = db.IntField(default=0, db_field='r')  # 用户组id 1管理员 2专家用户 3普通用户
    role = None  # 用户组权限
    domainid = db.IntField(default=1, db_field='di')  # 领域分类id
    industryid = db.IntField(default=1, db_field='ii')  # 行业分类id
    sex = db.IntField(default=1, db_field='s')  # 性别 1男 0女
    job = db.StringField(default='', max_length=64, db_field='j')  # 职位
    grade = db.IntField(db_field='g')  # 评级
    geo = db.PointField(default=[0, 0], db_field='ge')  # 坐标
    stats = db.EmbeddedDocumentField(
        UserStats, default=UserStats(), db_field='st')  # 统计
    date = db.IntField(default=0, db_field='d')  # 创建时间
    intro = db.StringField(default='', db_field='i')  # 简介
    content = db.StringField(default='', db_field='co')  # 简介内容
    bgurl = db.StringField(default='', db_field='b')  # 顶部背景图片
    fileurl = db.StringField(default='', db_field='f')  # 介绍图片或视频地址
    avaurl = db.StringField(default='', db_field='a')  # 头像地址
    label = db.ListField(default=[], db_field='l')  # 标签
    workexp = db.ListField(
        db.EmbeddedDocumentField(WorkExp), default=[], db_field='we')  # 工作经历
    edu = db.ListField(
        db.EmbeddedDocumentField(Edu), default=[], db_field='ed')  # 教育背景
    auth = db.EmbeddedDocumentField(UserAuth, default=UserAuth(), db_field='au')  # 用户认证
    state = db.IntField(default=1, db_field='sta')# 状态 1 正常  -1新增  -2待审核 0暂停
    sort = db.IntField(default=100, db_field='so')  # 排序
    thinktank = db.ListField(default=[], db_field='t')  # 智囊团
    wish = db.ListField(default=[], db_field='w')  # 心愿单
    money = db.IntField(default=0, db_field='m')  # 账户余额
    apptime = db.ListField(default=[], db_field='at')  # 预约时间（专家可预约时间）
    calltime = db.IntField(default=0, db_field='ct')  # 通话时间 (分享可获得)
    apptype = db.IntField(default=0, db_field='aty')  # 预约模式
    sns = db.EmbeddedDocumentField(SNS, default=SNS(), db_field='sn')
    openplatform = db.ListField(db.EmbeddedDocumentField(UserOpenPlatform), default=[], db_field='sp')  # 开放平台
    yuntongxunaccount = db.EmbeddedDocumentField(YuntongxunAccount, default=YuntongxunAccount(), db_field='ya') #容联云子帐号


    @staticmethod
    def getlist_app(roid=2,index=1,count=10):
        # 用于APP接口
        pageindex =(index-1)*count
        return User.objects(role_id=roid,state=1).order_by("sort").skip(pageindex).limit(count)

    @staticmethod
    def getlist(roid=0,index=1,count=10,sort='-_id'):
        #用于后端
        #.exclude('password_hash') 不包含字段
        pageindex =(index-1)*count
        if roid == 0:
            return User.objects.order_by(sort).skip(pageindex).limit(count)
        else:
            return User.objects(role_id=roid).order_by(sort).skip(pageindex).limit(count)

    @staticmethod
    def getcount(roid=0):
    	if roid == 0:
            return User.objects.count()
        else:
            return User.objects(role_id=roid).count()

    @staticmethod
    def getlist_uid_app(uidlist, feild=[], count=10):
        # 获取指定id列表的会员数据 用于后端
        #.exclude('password_hash') 不包含字段
        return User.objects(_id__in=uidlist,state=1).limit(
            count).exclude('password_hash')

    @staticmethod
    def getlist_uid(uidlist, feild=[], count=10):
        # 获取指定id列表的会员数据
        #.exclude('password_hash') 不包含字段

        ulist = []

        for item in uidlist:
            uinfo = User.objects(_id=item).exclude('password_hash').first()
            ulist.append(uinfo)

        return ulist
        #return User.objects(_id__in=uidlist).limit(
        #    count).exclude('password_hash')

    @staticmethod
    def getthinktanklist_uid(uidlist):
        # 获取智囊团列表
        return User.objects(_id__in=uidlist).exclude('password_hash')

    @staticmethod
    def getwishlist_uid(uidlist):
        # 获取心愿单列表
        return User.objects(_id__in=uidlist).exclude('password_hash')

    @staticmethod
    def getinfo_admin(username):
        # 获取指定id 管理员(web后台)

        query = Q(username=username) & (Q(role_id=1) | Q(role_id__gte=4))

        u_info = User.objects(query).first()

        if u_info is not None:
            u_info.role = Role.getinfo(u_info.role_id)
        return u_info

    @staticmethod
    def getinfo_app(username):
        # 获取指定id 用户(APP)

        query = Q(username=username) # & (Q(role_id=2) | Q(role_id=3))

        u_info = User.objects(query).first()

        if u_info is not None:
            u_info.role = Role.getinfo(u_info.role_id)
        return u_info

    @staticmethod
    def getinfo(uid, feild=[]):  # 获取指定id列表的会员数据
        #.exclude('password_hash') 不包含字段
        u_info = User.objects(_id=uid).exclude('password_hash').first()
        if u_info is not None:
            u_info.avaurl =  common.getavaurl(u_info.avaurl)
        return u_info
    @staticmethod
    def getadmininfo(uid):  # 获取指定id 管理员信息
        #.exclude('password_hash') 不包含字段
        query = Q(_id=uid) & (Q(role_id=1) | Q(role_id__gte=4))
        return User.objects(query).only('name').first()

    @staticmethod
    def getlist_geo_map(x, y,count=10, max=1000,roid=2):
    	#根据坐标获取数据列表 max最大距离(米)
        return User.objects(geo__near=[x, y],geo__max_distance=max,role_id=roid,state=1)

    @staticmethod
    def getlist_geo_list(x, y,industryid=0,count=10, max=1000):
    	#根据坐标获取数据列表 max最大距离(米)
    	query = Q(geo__near=[x, y]) & Q(geo__max_distance=max) &Q(role_id=2) & Q(state=1)
    	if industryid>0:
    		query = query & Q(industryid=industryid)
        list_count = User.objects(query).count()
        if list_count>=count:
            rand = common.getrandom()
            relist = []
            u_list = User.objects(query & Q(stats__rand__gte=rand))#大于等于  )|Q(_id__gte=rand)
            for item in u_list:
		        relist.append(item)
            if len(u_list)<count:
                ul_list = User.objects(query & Q(stats__rand__lte=rand))#小于等于 |Q(_id__lte=rand)
                for item in ul_list:
		        	relist.append(item)

            return relist
        else:
            return User.objects(query)

    @staticmethod
    def getexpertlist_app(industryid=0,index=1,count=10):
        #用于api
        #.exclude('password_hash') 不包含字段
        pageindex =(index-1)*count
        query = Q(role_id=2) & Q(state=1) & Q(sort__gt=0)
        if industryid>0:
            query = query & Q(industryid=industryid)
        return User.objects(query).exclude('password_hash').order_by("sort").skip(pageindex).limit(count)

    @staticmethod
    def isusername(username):
		#查找帐号是否存在 >0 存在   =0 不存在
		if len(username)>0:
			return User.objects(username=username).count()
		else:
			return -1

    def useredit(self):
        # 更新个人信息(用户)
        if self._id > 0:
            #print str(self._id)
            update = {}
            if len(self.name) > 0:
                update['set__name'] = self.name
            if self.sex>-1:
                update['set__sex'] = self.sex
            if len(self.avaurl)>0:
                update['set__avaurl'] = self.avaurl
            if self.role_id==2 or self.role_id==1:
                if self.domainid>-1:
                    update['set__domainid'] = self.domainid
                if self.industryid>-1:
                    update['set__industryid'] = self.industryid
            update['set__stats__lastaction'] = common.getstamp()
            User.objects(_id=self._id).update_one(**update)

    def updateworkexp(self):
        #更新工作经历 - 用户
        if self._id > 0:
            update = {}
            if len(self.workexp) > 0:
                update['set__workexp'] = self.workexp
                User.objects(_id=self._id).update_one(**update)
                return 1
        return 0

    def updateedu(self):
        #更新教育背景 - 用户
        if self._id > 0:
            update = {}
            if len(self.edu) > 0:
                update['set__edu'] = self.edu
                User.objects(_id=self._id).update_one(**update)
                return 1
        return 0

    @staticmethod
    def updatestate(uid,state):
        #更新用户状态 -2 -> 1
        update = {}
        update['set__state'] = state
        User.objects(_id=uid).update_one(**update)

    @staticmethod
    def updatephone(uid,newphone):
        #更新手机号
        #if g.current_user is not None:
        #    if g.current_user._id > 0:
        update = {}
        update['set__username'] = newphone
        User.objects(_id=uid).update_one(**update)
        return 1
        #return 0

    def updateforgetpaw(self):
        #忘记密码
        update = {}
        if len(self.password_hash) > 0:
            self.password = self.password_hash
            update['set__password_hash'] = self.password_hash
            User.objects(username=self.username).update_one(**update)
            return 1
        else:
            return 0

    @staticmethod
    def updatewish(uid,neweid,_type=1):
        #添加心愿单关注 1关注 0取消关注
        update = {}
        if _type==1:
            update['add_to_set__wish'] = neweid
        else:
            update['pull__wish'] = neweid
        User.objects(_id=uid).update_one(**update)
        return 1
        #return 0

    def updateintro(self):
        #更新简介 - 用户
        if self._id > 0:
            update = {}
            update['set__fileurl'] = self.fileurl
            update['set__intro'] = self.intro
            update['set__content'] = self.content
            update['set__label'] = self.label
            User.objects(_id=self._id).update_one(**update)
            return 1
        return 0

    def updateocp(self,_type):
        #认证专家 - 用户
        update = {}
        if _type==1:
            update['set__intro'] = self.intro

        elif _type==2:
            update['set__label'] = self.label
        elif _type==3:
            update['set__workexp'] = self.workexp
        elif _type==4:
            update['set__edu'] = self.edu
        elif _type==5:
            eaitem = ExpertAuth()
            eaitem.user_id = self._id
            eaitem.saveinfo()
        update['set__auth__expertprocess'] = _type
        User.objects(_id=self._id).update_one(**update)

    @staticmethod
    def updateexpert(uid):
        #更新认证专家状态
        update = {}
        update['set__auth__expert'] = 1
        update['set__role_id'] = 2
        User.objects(_id=uid).update_one(**update)

        u_info = User.objects(_id=uid).first()
        User.Create_Q_YUNSOU_DATA(u_info)

    @staticmethod
    def updatebecomeexpert(uid):
        #更新成为专家状态
        update = {}
        update['set__auth__becomeexpert'] = 1
        User.objects(_id=uid).update_one(**update)

    @staticmethod
    def updatesort(uid,sort):
        #更新排序
        update = {}
        update['set__sort'] = sort
        User.objects(_id=uid).update_one(**update)

    @staticmethod
    def updateapptime(uid,apptime):
        #更新专家预约时间
        update = {}
        update['set__apptime'] = apptime
        User.objects(_id=uid).update_one(**update)

    @staticmethod
    def updateshare(uid,_type):
        #更新分享获时间
        update = {}
        query=Q(_id=uid)
        nowtime = common.getdaystamp()
        if _type==1:
            update['set__stats__wxshare'] = nowtime
            query = query & Q(stats__wxshare__ne=nowtime)
        elif _type==2:
            update['set__stats__pyshare'] = nowtime
            query = query & Q(stats__pyshare__ne=nowtime)
        elif _type==3:
            update['set__stats__qqshare'] = nowtime
            query = query & Q(stats__qqshare__ne=nowtime)
        elif _type==4:
            update['set__stats__sinashare'] = nowtime
            query = query & Q(stats__sinashare__ne=nowtime)

        update['inc__calltime'] = conf.SHARE_CALL_TIME

        User.objects(query).update_one(**update)

    @staticmethod
    def updateapptype(uid,_type):
        #更新专家预约模式
        update = {}
        update['set__apptype'] = _type
        User.objects(_id=uid).update_one(**update)

    @staticmethod
    def updatemoney(uid,money):
        #充值金额更新
        update = {}
        update['inc__money'] = money
        User.objects(_id=uid).update_one(**update)

    @staticmethod
    def updateemail(uid,email):
        #更新邮箱 - 用户
        if uid > 0:
            update = {}
            update['set__email'] = email
            User.objects(_id=uid).update_one(**update)
            return 1
        return 0

    def updatebindphone(self):
        #更新第三方登录 绑定手机号 - 用户
        update = {}
        if len(self.username) > 0:
            update['set__username'] = self.username
        if len(self.password_hash) > 0:
            self.password = self.password_hash
            update['set__password_hash'] = self.password_hash
        User.objects(_id=self._id).update_one(**update)

    @staticmethod
    def updateYuntongxunAccount(uid,yta):
        #更新IM 子帐号
        if uid > 0:
            update = {}
            update['set__yuntongxunaccount'] = yta
            User.objects(_id=uid).update_one(**update)
            return 1
        return 0

    @staticmethod
    def updatecontact(uid,_type,val):
        #更新联系方式 微信 QQ (所有会员)
        update = {}
        if _type==1:
            update['set__weixin'] = val
        else:
            update['set__qq'] = val
        User.objects(_id=uid).update_one(**update)
        return 1

    @staticmethod
    def snslogin(sns,uid):
        query = None
        if sns==1:
            query=Q(sns__sina=uid)
        elif sns==2:
            query=Q(sns__qq=uid)
        elif sns==3:
            query=Q(sns__weixin=uid)
        return User.objects(query).first()

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)

        if self.username == '-1':
            self.username = 'sina_'+str(self._id)
        elif self.username == '-2':
            self.username = 'qq_'+str(self._id)
        elif self.username == '-3':
            self.username = 'weixin_'+str(self._id)
        elif len(self.username)==0:
            if self.role_id==2:
                self.username = 'zj_'+str(self._id)
            elif self.role_id==3:
                self.username = 'pt_'+str(self._id)

        self.password = self.password_hash
        self.date = common.getstamp()
        self.save()

        return self._id

    def saveinfo_app(self):
        #前端注册用户信息
        
        if len(self.username)==0:
                if self.role_id==2:
                    self.username = 'zj_'+str(self._id)
                elif self.role_id==3:
                    self.username = 'pt_'+str(self._id)
        istrue = User.isusername(username=self.username)
        if istrue == 0:
            self.password = self.password_hash
            self.date = common.getstamp()
            self.save()

            return self._id
        else:
            return -1

    def editinfo(self):
    	#后台更新用户信息
        if self._id > 0:
            update = {}
            # update.append({'set__email': self.email})
            update['set__role_id'] = self.role_id
            if len(self.email) > 0:
                update['set__email'] = self.email
            if len(self.username) > 0:
                update['set__username'] = self.username
            if len(self.name) > 0:
                update['set__name'] = self.name
            print self.password_hash
            if len(self.password_hash) > 0:
                self.password = self.password_hash
                update['set__password_hash'] = self.password_hash
            print self.password_hash
            update['set__confirmed'] = self.confirmed
            update['set__domainid'] = self.domainid
            update['set__industryid'] = self.industryid
            update['set__sex'] = self.sex
            update['set__job'] = self.job
            update['set__geo'] = self.geo
            update['set__intro'] = self.intro
            update['set__content'] = self.content
            update['set__bgurl'] = self.bgurl
            update['set__fileurl'] = self.fileurl
            update['set__avaurl'] = self.avaurl
            update['set__label'] = self.label
            update['set__workexp'] = self.workexp
            update['set__edu'] = self.edu
            update['set__openplatform'] = self.openplatform

            update['set__stats__lastaction'] = common.getstamp()
            '''
            update['set__stats__baidu'] = self.stats.baidu
            update['set__stats__weixin'] = self.stats.weixin
            update['set__stats__zhihu'] = self.stats.zhihu
            update['set__stats__sina'] = self.stats.sina
            update['set__stats__twitter'] = self.stats.twitter
            update['set__stats__facebook'] = self.stats.facebook
            update['set__stats__github'] = self.stats.github

            update['set__stats__baiduurl'] = self.stats.baiduurl
            update['set__stats__weixinurl'] = self.stats.weixinurl
            update['set__stats__zhihuurl'] = self.stats.zhihuurl
            update['set__stats__sinaurl'] = self.stats.sinaurl
            update['set__stats__twitterurl'] = self.stats.twitterurl
            update['set__stats__facebookurl'] = self.stats.facebookurl
            update['set__stats__githuburl'] = self.stats.githuburl
            '''
            update['set__state'] = self.state
            update['set__sort'] = self.sort
            User.objects(_id=self._id).update_one(**update)

            if self.role_id==2:
                User.Create_Q_YUNSOU_DATA(self)
            '''
            #更新whoosh
            updata_whoosh = {}
            updata_whoosh['_id']=self._id
            updata_whoosh['n']=unicode(self.name)
            updata_whoosh['l']=self.label
            updata_whoosh['j']=self.job
            searchwhoosh.update(updata_whoosh)
            '''
            logmsg = '编辑'+(self.role_id==2 and '用户'or '专家')+'-'+str(self._id)+'-'+self.name +'-' + self.job
            Log.saveinfo(remark=logmsg)

            return 1
        else:

            self._id = collection.get_next_id(self.__tablename__)
            if len(self.username)==0:
                    if self.role_id==2:
                        self.username = 'zj_'+str(self._id)
                    elif self.role_id==3:
                        self.username = 'pt_'+str(self._id)
            istrue = User.isusername(username=self.username)
            if istrue == 0:
                self.password = self.password_hash
                self.date = common.getstamp()
                self.save()

                if self.role_id==2:
                    User.Create_Q_YUNSOU_DATA(self)

                '''
                #更新whoosh
                updata_whoosh = {}
                updata_whoosh['_id']= self._id
                updata_whoosh['n']= unicode(self.name)
                updata_whoosh['j']= unicode(self.job)
                updata_whoosh['l']=self.label
                searchwhoosh.update(updata_whoosh)
                '''
                logmsg = '创建'+(self.role_id==2 and '用户'or '专家')+'-'+str(self._id)+'-'+self.name +'-' + self.job
                Log.saveinfo(remark=logmsg)

                return self._id
            else:
                return -1

    @staticmethod
    def list_search(roid,text, count=10):  # 后台搜索
        return User.objects((Q(name__icontains=text) | Q(job__icontains=text))&Q(role_id=roid)).limit(count).exclude('password_hash')
        #return User.objects((Q(name__istartswith=text) | Q(job__istartswith=text))&Q(role_id=roid)).limit(count).exclude('password_hash')

    @staticmethod
    def search(text, count=10):
        # 专家搜索
        return User.objects( Q(state=1) & Q(role_id=2) & (Q(name__istartswith=text) | Q(job__istartswith=text))).limit(count).only('name','job')

    @staticmethod
    def Create_Q_YUNSOU_DATA(data):
        #添加 腾讯云 云搜数据
        try:
            params = {
                    "appId" : conf.QCLOUDAPI_YUNSOU_APPID,
                    "op_type":"add",
                    "contents.0.id" :data._id,
                    "contents.0.name" : data.name,
                    "contents.0.job" : data.job,
                    "contents.0.label" : ";".join(data.label),
                    "contents.0.state" : data.state
            }
            msg = q_search.call(Q_SOUYUN_ACTION, params)
            ret = json.loads(msg)
            if ret['retcode'] is not 0:
                logging.debug(msg)
        except Exception,e:
            logging.debug(e)

    @staticmethod
    def Update_Q_YUNSOU_STATE(id,state):
        #更新 腾讯云 云搜专家状态

        try:
            u_info = User.getinfo(id)
            if u_info is not None:
                params = {
                        "appId" : conf.QCLOUDAPI_YUNSOU_APPID,
                        "op_type":"add",
                        "contents.0.id" :id,
                        "contents.0.name" : u_info.name,
                        "contents.0.job" : u_info.job,
                        "contents.0.label" : ";".join(u_info.label),
                        "contents.0.state" : state
                    }
                msg = q_search.call(Q_SOUYUN_ACTION, params)
                ret = json.loads(msg)
                if ret['retcode'] is not 0:
                    logging.debug(msg)
        except Exception,e:
            logging.debug(e)

    @staticmethod
    def Q_YUNSOU(text,pageindex=1,count=10):
        #搜索 腾讯云 云搜数据
        try:
            params = {
                "appId" : conf.QCLOUDAPI_YUNSOU_APPID,
                "search_query" : text,
                "page_id" : pageindex-1,
                "num_per_page" : count,
                "num_filter":'[N:state:1:1]'
            }
            msg = q_search.call(Q_SOUYUN_SEARCH, params)
            ret = json.loads(msg)
            if ret['code'] is 0:
                return ret
            #else:
            #    logging.debug(msg)
        except Exception,e:
            logging.debug(e)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASK_ADMIN']:
                self.role = Role.objects(permissions=0xff).first()
            if self.role is None:
                self.role = Role.objects(default=True).first()
        '''
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        '''
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password

        update = {}
        update['set__password_hash'] = self.password_hash
        update['set__stats__lastaction'] = common.getstamp()
        User.objects(_id=self._id).update_one(**update)

        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})
    '''

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        # db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and
            (self.role.permissions & permissions) == permissions
    '''

    def can(self,name, permissions):
        #return self.role is not None and (getattr(self.role['permissions'],name) & permissions) == permissions
        return self.role is not None and (self.role['permissions'][name] & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)
    '''

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
    '''

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def to_json(self, type=0):  # type 0默认 1简短 2... 3...
        if type == -1:
            #专家详情
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'sex': self.sex,
                'job': self.job.encode('utf-8'),
                'auth': {'expert': self.auth.expert,'expertprocess': self.auth.expertprocess},  # self.auth.vip
                'grade': common.getgrade(self.stats.comment_count, self.stats.comment_total),
                'meet_c': self.stats.meet,
                'follow':[item.to_json() for item in self.openplatform],
                #'follow':[{'baidu':self.stats.baidu,'baiduurl':self.stats.baiduurl},{'weixin':self.stats.weixin,'weixinurl':self.stats.weixinurl},{'zhihu':self.stats.zhihu,'zhihuurl':self.stats.zhihuurl},{'sina':self.stats.sina,'sinaurl':self.stats.sinaurl},{'twitter':self.stats.twitter,'twitterurl':self.stats.twitterurl},{'facebook':self.stats.facebook,'facebookurl':self.stats.facebookurl},{'github':self.stats.github,'githuburl':self.stats.githuburl}],
                # [39.9442, 116.324]
                'geo': [self.geo['coordinates'][1], self.geo['coordinates'][0]],
                'intro': self.intro.encode('utf-8'),
                'content': self.content.encode('utf-8'),
                'bgurl': self.bgurl.encode('utf-8'),
                'fileurl': self.fileurl.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl),#common.getavatar(userid=self.id)
                'work': [item.to_json() for item in self.workexp],
                'edu': [item.to_json() for item in self.edu],
                'label':self.label,
                'role_id':self.role_id,
                'domainid':self.domainid,
                'industryid':self.industryid,
                'phone':self.username
            }
        elif type == 0:
            #普通用户
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'sex': self.sex,
                'job': self.job.encode('utf-8'),
                'auth': {'becomeexpert': self.auth.becomeexpert,'expertprocess': self.auth.expertprocess}, # self.auth.vip
                'grade': common.getgrade(self.stats.comment_count, self.stats.comment_total),
                'meet_c': self.stats.meet,
                # [39.9442, 116.324]
                'geo': [self.geo['coordinates'][1], self.geo['coordinates'][0]],
                'intro': self.intro.encode('utf-8'),
                'fileurl': self.fileurl.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl),#common.getavatar(userid=self.id)
                'work': [item.to_json() for item in self.workexp],
                'edu': [item.to_json() for item in self.edu],
                'label':self.label,
                'role_id':self.role_id,
                'domainid':self.domainid,
                'industryid':self.industryid,
                'money':self.money,
                'apptime':self.apptime,
                'calltime':self.calltime,
                'wish':self.wish,
                'calltype':(self.apptype&0x01)==0x01 and 1 or 0, #通话模式开启
                'meettype':(self.apptype&0x02)==0x02 and 1 or 0, #见面模式开启
                'phone':self.username,
                'weixin':self.weixin,
                'qq':self.qq,
                'email':self.email
            }
        elif type == 1:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl)
            }
        elif type == 2:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'intro': self.intro.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl)
            }
        elif type == 3:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl)
            }
        elif type == 4:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl),
                'grade': common.getgrade(self.stats.comment_count, self.stats.comment_total),
                'auth': {'vip': 1},
                'stats': self.stats.to_json(),
                'sex': self.sex
            }
        elif type == 5:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavaurl(self.avaurl),
                'grade': common.getgrade(self.stats.comment_count, self.stats.comment_total),
                'auth': {'vip': 1}
            }
        elif type == 6:
        	#地图专家列表
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'geo': [self.geo['coordinates'][1], self.geo['coordinates'][0]],
                'avaurl': common.getavaurl(self.avaurl),
                'grade': common.getgrade(self.stats.comment_count, self.stats.comment_total),
                'auth': {'vip': 1}
            }

        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        # token =
        # 'eyJhbGciOiJIUzI1NiIsImV4cCI6MTQzMzkzMDUwNiwiaWF0IjoxNDMzOTI2OTA2fQ.eyJpZCI6NH0.kf4L_xi-7vF655_g6-y7XgajANtzkPsFVnxYDp8g0ZY'

        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        return User.objects().get(_id=data['id'])

    def __repr__(self):
        return '<User %r>' % self.username


class TopicConfig(db.EmbeddedDocument):  # 工作经历
    background = db.StringField(
        default='', db_field='b')  # 背景图片地址

    def to_json(self):
        json_tc = {
            'background': self.background.encode('utf-8')
        }
        return json_tc


class TopicStats(db.EmbeddedDocument):  # 话题统计
    topic_count = db.IntField(default=0, db_field='tc')  # 评论人数
    topic_total = db.IntField(default=0, db_field='tt')  # 评论总分
    like = db.IntField(default=0, db_field='l')  # 喜欢数

    def to_json(self):
        json_ts = {
            'count': self.topic_count,
            'total': self.topic_total,
            'like': self.like
        }
        return json_ts

class TopicPay(db.EmbeddedDocument):  # 支付价格
    call = db.IntField(default=0, db_field='c')  # 通话价格
    calltime = db.IntField(default=0, db_field='ct')  # 通话时间
    meet = db.IntField(default=0, db_field='m')  # 见面价格
    meettime = db.IntField(default=0, db_field='mt')  # 见面时间

    def to_json(self):
        json_tp = {
            'call': self.call,
            'calltime': self.calltime,
            'meet': self.meet,
            'meettime': self.meettime,
        }
        return json_tp


class Topic(db.Document):  # 话题
    __tablename__ = 'topics'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    user_id = db.IntField(default=0, db_field='u')  # 用户id，0为官方话题
    title = db.StringField(
        default='', max_length=64, required=True, db_field='t')
    intro = db.StringField(default='', max_length=256, db_field='i')
    content = db.StringField(default='', db_field='c')
    pay = db.EmbeddedDocumentField(TopicPay, default=TopicPay(), db_field='p')
    grade = db.IntField(db_field='g')
    date = db.IntField(default=common.getstamp(), db_field='d')
    expert = db.ListField(db_field='e')  # 关联专家
    config = db.EmbeddedDocumentField(
        TopicConfig, default=TopicConfig(), db_field='tc')  # 话题配置信息
    stats = db.EmbeddedDocumentField(
        TopicStats, default=TopicStats(), db_field='ts')  # 话题统计信息
    sort = db.IntField(default=0, db_field='s')  # 排序
    discoverysort = db.IntField(default=0, db_field='ds')  # 发现首页排序
    state = db.IntField(default=0, db_field='st')# 状态 1 正常 0待审核 -1已删除

    @staticmethod
    def updatestate(tid,state):
        #更新话题状态 0 -> 1
        update = {}
        update['set__state'] = state
        Topic.objects(_id=tid).update_one(**update)
    
    @staticmethod
    def getlist_app(uid=0,index=1, count=10):
        # 获取列表 0全部  -1官方  -2专家  -3发现首页
        uid = int(uid)
        pageindex =(index-1)*count
        sort = 'sort'
        if uid == 0:
            return Topic.objects(state=1).exclude('content').order_by(sort).skip(pageindex).limit(count)
        elif uid == -1:
            return Topic.objects(user_id=0,state=1,discoverysort__gt=0).exclude('content').order_by('discoverysort').skip(pageindex).limit(count)
        elif uid == -2:
            return Topic.objects(user_id__gt=0,state=1).exclude('content').order_by(sort).skip(pageindex).limit(count)
        elif uid == -3:
            return Topic.objects(user_id__gt=0,state=1,discoverysort__gt=0).exclude('content').order_by('discoverysort').skip(pageindex).limit(count)
        else:
            return Topic.objects(user_id=uid,state=1).exclude('content').order_by(sort).skip(pageindex).limit(count)

    @staticmethod
    def getlist_recycle(index=1, count=10):
        # 获取列表 话题回收站
        pageindex =(index-1)*count
        return Topic.objects(state=-1).exclude('content').order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getlist(uid=0,index=1, count=10,state=1):
    	# 获取列表 0全部  -1官方  -2专家
        uid = common.strtoint(uid,0)
        pageindex =(index-1)*count
        query=None
        sort = '-_id'
        if state==1:
            query = Q(state__gte=0)
        else:
            query = Q(state=-1)
        if uid == 0:
            return Topic.objects(query).exclude('content').order_by(sort).skip(pageindex).limit(count)
        elif uid == -1:
            query=query&Q(user_id=0)
            return Topic.objects(query).exclude('content').order_by(sort).skip(pageindex).limit(count)
        elif uid == -2:
            query=query&Q(user_id__gt=0)
            return Topic.objects(query).exclude('content').order_by(sort).skip(pageindex).limit(count)
        else:
            query=query&Q(user_id=uid)
            return Topic.objects(query).exclude('content').order_by(sort).skip(pageindex).limit(count)

    @staticmethod
    def list_search(uid,text, count=10):  # 后台搜索
        uid = int(uid)
        query = Q(title__istartswith=text)
        if uid == -1 :
            query = query & Q(user_id=0)
        elif uid==-2:
            query = query & Q(user_id__gt=0)
        query = query & Q(state__gte=0)
        return Topic.objects(query).limit(count).exclude('content')

    @staticmethod
    def getcount_recycle():
        # 话题回收站数量
        return Topic.objects(state=-1).count()

    @staticmethod
    def getcount(uid=0,state=1):
        uid = common.strtoint(uid,-10)
        if uid>-10:
            if state==1:
                query = Q(state__gte=0)
            else:
                query = Q(state=-1)
            if uid == 0:
                return Topic.objects(query).count()
            elif uid == -1:
                query = query & Q(user_id=0)
                return Topic.objects(query).count()
            elif uid == -2:
                query = query & Q(user_id__gt=0)
                return Topic.objects(query).count()
            else:
                query = query & Q(user_id=uid)
                return Topic.objects(query).count()
        else:
            return 0

    @staticmethod
    def getinfo(tid=0):
        return Topic.objects.get(_id=tid)

    @staticmethod
    def getinfo_expert(tid):  # 获取话题的专家id列表(expert字段)
        #.exclude('password_hash') 不包含字段
        return Topic.objects.only('expert').get(_id=tid)

    @staticmethod
    def delinfo(tid):
        #删除话题 设置话题状态
        update = {}
        update['set__state'] = -1
        Topic.objects(_id=tid).update_one(**update)

    @staticmethod
    def updatediscoverysort(tid,val):
        #更新排序 discoverysort
        update = {}
        update['set__discoverysort'] = val
        Topic.objects(_id=tid).update_one(**update)

    def saveinfo_app(self):
        if self._id > 0:
            update = {}
            # update.append({'set__email': self.email})

            update['set__user_id'] = self.user_id
            if len(self.title) > 0:
                update['set__title'] = self.title
            #if len(self.intro) > 0:
            #    update['set__intro'] = self.intro
            update['set__content'] = self.content
            update['set__pay__call'] = self.pay.call
            update['set__pay__meet'] = self.pay.meet
            update['set__pay__calltime'] = self.pay.calltime
            update['set__pay__meettime'] = self.pay.meettime

            #update['set__sort'] = self.sort
            Topic.objects(_id=self._id,user_id=self.user_id).update_one(**update)
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            return self._id

    def editinfo(self,_type=0):
        # _type 0话题  1话题团
        if self._id > 0:
            update = {}
            # update.append({'set__email': self.email})


            if len(self.title) > 0:
                update['set__title'] = self.title
            if len(self.intro) > 0:
                update['set__intro'] = self.intro
            if len(self.content) > 0:
                update['set__content'] = self.content

            if _type==1:
                update['set__state'] = self.state
                update['set__expert'] = self.expert
                update['set__config__background'] = self.config.background
            else:
                update['set__user_id'] = self.user_id
                update['set__pay__call'] = self.pay.call
                update['set__pay__meet'] = self.pay.meet
                update['set__pay__calltime'] = self.pay.calltime
                update['set__pay__meettime'] = self.pay.meettime
                update['set__stats__topic_count'] = self.stats.topic_count
                update['set__stats__topic_total'] = self.stats.topic_total
            update['set__sort'] = self.sort
            update['set__discoverysort'] = self.discoverysort

            Topic.objects(_id=self._id).update_one(**update)

            logmsg = '编辑话题-'+str(self._id)+'-'+self.title
            Log.saveinfo(remark=logmsg)
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            logmsg = '创建话题-'+str(self._id)+'-'+self.title
            Log.saveinfo(remark=logmsg)
            return self._id

    def to_json(self, type=0):  # 0默认 1发现首页专家团  2发现首页专家话题
        if type == 0:
            json_topic = {
                '_id': self.id,
                'user_id': self.user_id,
                'title': self.title.encode('utf-8'),
                'intro': self.intro.encode('utf-8'),
                'pay': self.pay.to_json(),  # self.auth.vip
                'grade': common.getgrade(self.stats.topic_count, self.stats.topic_total)
                #'config': self.config.to_json()
            }
        elif type == 1:
            #专家团列表
            json_topic = {
                '_id': self.id,
                'type': 1,  # 1为专家团
                'title': self.title.encode('utf-8'),
                'intro': self.intro.encode('utf-8'),
                #'date': self.date,
                'exp_count': len(self.expert),
                'expert': [item.to_json(1) for item in User.getlist_uid(uidlist=self.expert)],
                'stats': self.stats.to_json()
            }
        elif type == 3:
            #专家团详情页
            json_topic = {
                '_id': self.id,
                'type': 1,  # 1为专家团
                'title': self.title.encode('utf-8'),
                #'intro': self.intro.encode('utf-8'),
                'content': self.content.split('{split}'),#内容用 {split} 分割
                #'exp_count': len(self.expert),
                'expert': [item.to_json(5) for item in User.getlist_uid(uidlist=self.expert)],
                'like': self.stats.like,
                'background':self.config.background
            }
        elif type == 2:
            #发现首页（单专家）
            if self.user_id > 0:
                u_info = User.getinfo(uid=self.user_id)

            json_topic = {
                '_id': self.id,
                'type': 0,  # 0为专家
                'title': self.title.encode('utf-8'),
                'intro': self.intro.encode('utf-8'),
                'date': self.date,
                'expert': u_info is not None and u_info.to_json(3) or {},
                'stats': self.stats.to_json()

                #'expert': [50, 38, 47, 39]
            }

        return json_topic


class Comment(db.Document):  # 评论
    __tablename__ = 'comments'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    user_id = db.IntField(
        default=0, required=True, db_field='u')  # , db_field='e'
    name = db.StringField(
        default='', max_length=64, required=True, db_field='n')
    top_id = db.IntField(default=0, required=True, db_field='t')
    top_title = db.StringField(
        default='', max_length=64, required=True, db_field='tt')
    content = db.StringField(default='', db_field='c')
    date = db.IntField(default=common.getstamp(), db_field='d')
    grade = db.IntField(default=0, db_field='g')

    @staticmethod
    def getlist(uid, page=1, count=10):
        #.exclude('password_hash') 不包含字段
        return Comment.objects(user_id=uid).limit(count)

    @staticmethod
    def getcount(tid):
        return Comment.objects(top_id=tid).count()

    def to_json(self):
        json_topic = {
            '_id': self.id,
            'user_id': self.user_id,
            'name': self.name.encode('utf-8'),
            'top_id': self.top_id,
            'top_title': self.top_title.encode('utf-8'),  # self.auth.vip
            'content': self.content.encode('utf-8'),
            'date': self.date,
            'grade': self.grade,
            'avaurl':'' #common.getavaurl(self.avaurl)
        }
        return json_topic


class AnonymousUser(AnonymousUserMixin):

    confirmed=True #允许访问公共api

    def can(self, permissions):
        return False

    def is_administrator(self):
        return False # 游客

login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()


class collection(db.Document):
    meta = {
        'collection': 'collection',
    }
    name = db.StringField(max_length=30, required=True)
    index = db.IntField(required=True)

    @staticmethod
    def get_next_id(tablename):
        doc = collection.objects(name=tablename).modify(inc__index=1)
        if doc:
            return doc.index + 1
        else:
            collection(name=tablename, index=1).save()
            return 1 # 自增id


class InvTopicStats(db.EmbeddedDocument):  # 清单话题统计
    like = db.IntField(default=0, db_field='l')  # 喜欢数量

    def to_json(self):
        json = {
            'like': self.like
        }
        return json


class InvTopic(db.EmbeddedDocument):  # 清单话题
    _id = db.IntField(db_field='i')  # id
    title = db.StringField(default='', max_length=64,  db_field='t')  # 标题
    content = db.StringField(default='', db_field='c')  # 内容
    expert = db.ListField(db_field='e')  # 关联专家
    sort = db.IntField(default=0, db_field='s')  # 排序
    stats = db.EmbeddedDocumentField(
        InvTopicStats, default=InvTopicStats(), db_field='st')  # 话题统计信息

    def to_json(self):
        json_invt = {
            '_id': self._id,
            'title': self.title.encode('utf-8'),
            'content': self.content.encode('utf-8'),
            'expert': [item.to_json(3) for item in User.getlist_uid(uidlist=self.expert)],
            'sort': self.sort
        }
        return json_invt


class Inventory(db.Document):  # 清单
    __tablename__ = 'inventory'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)  # id
    title = db.StringField(default='', max_length=64, db_field='t')  # 标题
    date = db.IntField(default=common.getstamp(), db_field='d')  # 创建时间
    topic = db.ListField(
        db.EmbeddedDocumentField(InvTopic), db_field='to')  # 清单话题
    sort = db.IntField(default=0, db_field='s')  # 排序

    @staticmethod
    def getcount():
        return Inventory.objects.count()

    @staticmethod
    def getlist(index=1,count=10):
        pageindex =(index-1)*count
        return Inventory.objects.exclude('topic').order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getinfo(iid=0):
        return Inventory.objects.get(_id=iid)

    @staticmethod
    def getexpertlist(iid,tid):
        #获取清单专家列表  iid清单id   tid话题id
        return Inventory.objects(Q(_id=iid)&Q(topic__S___id=tid))

    def editinfo(self):
        if self._id > 0:
            update = {}
            if len(self.title) > 0:
                update['set__title'] = self.title

            update['set__topic'] = self.topic
            update['set__sort'] = self.sort
            Inventory.objects(_id=self._id).update_one(**update)

            logmsg = '编辑清单-'+str(self._id)+'-'+self.title
            Log.saveinfo(remark=logmsg)
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            logmsg = '创建清单-'+str(self._id)+'-'+self.title
            Log.saveinfo(remark=logmsg)
            return self._id

    def to_json(self):
        json_inv = {
            '_id': self.id,
            'title': self.title.encode('utf-8'),
            'date': self.date,
            'invtopic': [item.to_json() for item in self.topic],
            'sort': self.sort
        }
        return json_inv


class Ad(db.Document):  # 广告
    __tablename__ = 'ad'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    title = db.StringField(
        default='', max_length=64, required=True, db_field='t')
    group_id = db.IntField(default=0, required=True, db_field='g')  # 分组id 0未分组 1清单 
    fileurl = db.StringField(default='', db_field='fu')  # 文件地址
    url = db.StringField(db_field='u')  # 跳转地址或 跳转id
    sort = db.IntField(default=0, db_field='s')  # 排序

    @staticmethod
    def getlist_app(gid=0,index=1, count=10):
        pageindex =(index-1)*count
        sort='sort'
        if gid is 0:
            return Ad.objects.order_by(sort).skip(pageindex).limit(count)
        else:
            return Ad.objects(group_id=gid).order_by(sort).skip(pageindex).limit(count)

    @staticmethod
    def getlist(gid=0,index=1, count=10):
        pageindex =(index-1)*count

        if gid == 0:
            return Ad.objects.order_by("-_id").skip(pageindex).limit(count)
        else:
            return Ad.objects(group_id=gid).order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount(gid=0):
        if gid == 0:
            return Ad.objects.count()
        else:
            return Ad.objects(group_id=gid).count()

    @staticmethod
    def getinfo(aid):
        return Ad.objects.get(_id=aid)

    def editinfo(self):
        if self._id > 0:
            update = {}
            if len(self.title) > 0:
                update['set__title'] = self.title

            update['set__group_id'] = self.group_id
            update['set__fileurl'] = self.fileurl
            update['set__url'] = self.url
            update['set__sort'] = self.sort
            Ad.objects(_id=self._id).update_one(**update)

            logmsg = '编辑广告-'+str(self._id)+'-'+self.title
            Log.saveinfo(remark=logmsg)
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            logmsg = '创建广告-'+str(self._id)+'-'+self.title
            Log.saveinfo(remark=logmsg)
            return self._id

    @staticmethod
    def delinfo(aid):
        Ad.objects(_id=aid).delete()

    def to_json(self):
        json_ad = {
            '_id': self.id,
            'title': self.title.encode('utf-8'),
            'fileurl': self.fileurl.encode('utf-8'),
            'url': self.url.encode('utf-8'),
            'sort': self.sort,
        }
        return json_ad


class Appointment(db.Document):  # 预约
    __tablename__ = 'appointment'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    user_id = db.IntField(default=0, required=True, db_field='ui')  # 发起预约的会员ID
    appid = db.IntField(default=0, required=True, db_field='ai')  # 被约会员的ID
    topic_id = db.IntField(default=0, db_field='ti')  # 话题id
    topic_title = db.StringField(default='', db_field='tt')  # 话题标题
    appdate = db.IntField(default=0, db_field='ad')  # 预约时间
    apptype = db.IntField(default=1, db_field='at')  # 预约方式 1通话 2见面 3立即通话
    time =  db.IntField(default=0, db_field='t')  # 通话/见面 时间(分钟)
    address = db.StringField(default='', db_field='a')  # 预约地址
    price = db.IntField(default=0, db_field='p')  # 支付价格
    attachment = db.ListField(default=[], db_field='att')  # 附件
    remark = db.StringField(default='', db_field='r')  # 备注
    state = db.IntField(default=0, db_field='s')  # 预约状态 0订单失败 1申请中 2待付款 3进行中 4等待用户确认 5已完成
    cancelremark = db.StringField(default='', db_field='cr')  # 取消备注
    paystate = db.IntField(default=0, db_field='ps')  # 支付状态 0未支付 1已支付
    date = db.IntField(default=0, db_field='d')  # 创建时间

    @staticmethod
    # _type=1我约 _type=2被约  /  appid 约/被约 专家id
    def getcount(_type=0, appid=0):
        if _type == 0:
            return Appointment.objects().count()
        elif _type == 2:
            return Appointment.objects(appid=appid).count()
        elif _type == 1:
            return Appointment.objects(user_id=appid).count()

    @staticmethod
    # _type=1我约 _type=2被约  /  appid 约/被约 专家id
    def getlist(_type=0, appid=0, index=1, count=10):
        pageindex =(index-1)*count
        if _type == 0:
            return Appointment.objects().order_by("-date").skip(pageindex).limit(count)
        elif _type == 2:
            return Appointment.objects(appid=appid).order_by("-date").skip(pageindex).limit(count)
        elif _type == 1:
            return Appointment.objects(user_id=appid).order_by("-date").skip(pageindex).limit(count)

    @staticmethod
    def getinfo(aid):
        return Appointment.objects(_id=aid).first()

    @staticmethod
    def createid():
        # 生成自增id
        aid = collection.get_next_id(Appointment.__tablename__)
        return int(common.getappointmentid(aid))

    @staticmethod
    def updateappstate(aid,state,apptype):
        #更新订单状态 -- 后台
        update = {}
        update['set__state'] = state
        update['set__apptype'] = apptype
        if state==3:
            update['set__paystate'] = 1
        elif state==1 or state==2:
            update['set__paystate'] = 0

        if apptype==3:
            update['set__appdate'] = 0

        Appointment.objects(_id=aid).update_one(**update)

    @staticmethod
    def updateappstate_app(aid,state,paystate=-1,uid=0,time=0,cancelremark=''):
        #更新订单状态
        query = Q(_id=aid)
        update = {}
        update['set__state'] = state
        if paystate>-1:
            update['set__paystate'] = paystate
        if uid>0:
            if state==0 or state==2 or state==4 or state==-1:
                query = query & Q(appid=uid) 
                if state==4 and time>0:
                    update['set__time'] = time
                elif state==-1:
                    update['set__cancelremark'] = cancelremark
            else:
                query = query & Q(user_id=uid)
        Appointment.objects(query).update_one(**update)

    def editinfo(self):
        #创建订单信息
        self._id = Appointment.createid()
        self.date = common.getstamp()
        try:
            self.save()
        except Exception, e:
            logging.debug(e)
            self._id = Appointment.createid()
            self.save()
        return self._id

    def to_json(self, uid, type=1):  # type返回相应字段 1列表 0详情
        if uid<3:
            uinfo = User.getinfo(uid == 1 and self.appid or self.user_id)
        else:
            uinfo = User.getinfo(uid == self.user_id and self.appid or self.user_id)
        if uinfo is not None:
            if type == 1:
                json_app = {
                    '_id': str(self.id),
                    'info': uinfo.to_json(3),
                    'user_id': self.user_id,
                    'appid': self.appid,
                    'topic_id': self.topic_id,
                    'topic_title': self.topic_title.encode('utf-8'),
                    'appdate': self.appdate,
                    'apptype': self.apptype,
                    'type': uid == self.user_id and 1 or 2, # 约状态  1我约  2被约
                    #'address': self.address.encode('utf-8'),
                    'price': self.price,
                    #'attachment': self.attachment,
                    #'remark': self.remark.encode('utf-8'),
                    'state': self.state,
                    'paystate': self.paystate
                }
            else:  # 0
                json_app = {
                    '_id': str(self.id),
                    'date': self.date,
                    'info': uinfo.to_json(3),
                    'user_id': self.user_id,
                    'appid': self.appid,
                    'topic_id': self.topic_id,
                    'topic_title': self.topic_title.encode('utf-8'),
                    'appdate': self.appdate,
                    'apptype': self.apptype,
                    'address': self.address.encode('utf-8'),
                    'price': self.price,
                    'attachment': self.attachment,
                    'remark': self.remark.encode('utf-8'),
                    'state': self.state,
                    'paystate': self.paystate,
                    'phone': uinfo.username
                }
            return json_app
        else:
            return {}

class Log(db.Document):  
    # 管理员日志
    __tablename__ = 'log'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    remark = db.StringField(default='', db_field='r')  # 备注
    date = db.IntField(default=common.getstamp(), db_field='d')  # 创建时间
    admin_id = db.IntField(default=0, db_field='a')  # 管理员ID

    @staticmethod
    def saveinfo(remark='',aid=0):
        Log(remark=remark,admin_id=aid==0 and g.current_user._id or aid,_id=collection.get_next_id(Log.__tablename__),date=common.getstamp()).save()

    @staticmethod
    def getlist(aid=0,index=1, count=10):
    	# 获取列表 0全部  -1官方  -2专家
        pageindex =(index-1)*count
        if aid == 0:
            return Log.objects.order_by("-_id").skip(pageindex).limit(count)
        else:
            return Log.objects(admin_id=aid).order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount(aid=0):
    	if aid == 0:
            return Log.objects.count()
        else:
            return Log.objects(admin_id=aid).count()

class Message(db.Document):  
    # 消息
    __tablename__ = 'message'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    user_id = db.IntField(default=0, db_field='u')  # 用户id
    appointment_id = db.IntField(default=0, db_field='a')  # 预约订单id
    date = db.IntField(default=0, db_field='d')  # 创建时间
    type = db.IntField(default=0, db_field='ty')  # 消息类型 1成功 2失败 3温馨提醒 4消息提醒
    title = db.StringField(default='', db_field='t')  # 标题
    content = db.StringField(default='', db_field='c')  # 内容

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)
        self.date = common.getstamp()
        self.save()

    @staticmethod
    def getlist(uid,index=1, count=10):
        pageindex =(index-1)*count
        return Message.objects(user_id=uid).order_by("-_id").skip(pageindex).limit(count)

    def to_json(self):
        json_message = {
            '_id': self.id,
            'title': self.title.encode('utf-8'),
            'content': self.content.encode('utf-8'),
            'appointment_id': self.appointment_id,
            'date': self.date,
            'type': self.type
        }
        return json_message

class PayLog(db.Document):  
    # 充值日志
    __tablename__ = 'paylog'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    created = db.IntField(default=0, db_field='c') 
    paid = db.BooleanField(default=False, db_field='p')
    app =  db.StringField(default='', db_field='a')
    channel =  db.StringField(default='', db_field='ch')
    order_no =  db.StringField(default='', db_field='o')
    #client_ip
    amount =  db.IntField(default='', db_field='am')
    amount_settle =  db.IntField(default='', db_field='ams')
    currency =  db.StringField(default='', db_field='cu')
    subject =  db.StringField(default='', db_field='s')
    body =  db.StringField(default='', db_field='b')
    time_paid =  db.IntField(default='', db_field='t')  # 支付成功时间
    time_expire =  db.IntField(default='', db_field='te')
    transaction_no =  db.StringField(default='', db_field='tr')
    amount_refunded =  db.IntField(default=0, db_field='ar')
    failure_code =  db.StringField(default='', db_field='f')
    failure_msg =  db.StringField(default='', db_field='fa')
    description =  db.StringField(default='', db_field='d')

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)
        self.save()

class ExpertInv(db.Document):
    #专家清单
    __tablename__ = 'expertinv'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)  # id
    title = db.StringField(default='', max_length=64,  db_field='t')  # 标题
    content = db.StringField(default='', db_field='c')  # 内容
    user_id = db.IntField(db_field='ui')  # 专家ID
    date = db.IntField(default=0, db_field='d')  # 创建时间
    price = db.IntField(default=0, db_field='p')  # 支付价格
    unit = db.IntField(default='', db_field='u')  # 单位
    sort = db.IntField(default=0, db_field='s')  # 排序

    def saveinfo(self):
        if self._id > 0:
            update = {}
            if len(self.title) > 0:
                update['set__title'] = self.title
            update['set__content'] = self.content
            update['set__price'] = self.price
            update['set__unit'] = self.unit
            #update['set__sort'] = self.sort
            ExpertInv.objects(_id=self._id,user_id=self.user_id).update_one(**update)
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.date = common.getstamp()
            self.save()

    @staticmethod
    def getlist(uid,index=1, count=10):
        pageindex =(index-1)*count
        return ExpertInv.objects(user_id=uid).order_by("sort").skip(pageindex).limit(count)

    def to_json(self):
        json_invt = {
            '_id': self._id,
            'title': self.title.encode('utf-8'),
            'content': self.content.encode('utf-8'),
            'price': self.price,
            'unit': self.unit.encode('utf-8'),
            'sort': self.sort
        }
        return json_invt

class ExpertAuth(db.Document):
    #专家认证审核
    __tablename__ = 'expertauth'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)  # id
    user_id = db.IntField(default=0, db_field='ui')  # 专家ID
    state = db.IntField(default=0, db_field='s')  # 1审核通过 0审核中
    date = db.IntField(default=0, db_field='d')  # 创建时间
    admin_id =  db.IntField(default=0, db_field='ai')  # 操作人


    @staticmethod
    def getinfo(eid):
        return ExpertAuth.objects(_id=eid).first()

    @staticmethod
    def getlist(index=1, count=10):
        pageindex =(index-1)*count
        return ExpertAuth.objects.order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount():
        return ExpertAuth.objects.count()

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)
        self.date = common.getstamp()
        self.save()

    @staticmethod
    def updatestate(eid):
        #更新审核状态
        update = {}
        update['set__state'] = 1
        ExpertAuth.objects(_id=eid).update_one(**update)

class BecomeExpert(db.Document):
    #成为审核
    __tablename__ = 'becomeexpert'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)  # id
    user_id = db.IntField(default=0, db_field='ui')  # 用户ID
    name = db.StringField(default='', db_field='n')  # 姓名
    #industry = db.StringField(default='', db_field='i')  # 行业
    #company = db.StringField(default='', db_field='c')  # 公司
    #job = db.StringField(default='', db_field='j')  # 职位
    phone = db.StringField(default='', db_field='p')  # 职位
    weixin = db.StringField(default='', db_field='w')  # 微信号
    qq = db.StringField(default='', db_field='q')  # QQ
    date = db.IntField(default=0, db_field='d')  # 创建时间

    @staticmethod
    def getlist(index=1, count=10):
        pageindex =(index-1)*count
        return BecomeExpert.objects.order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount():
        return BecomeExpert.objects.count()

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)
        self.date = common.getstamp()
        self.save()
        User.updatebecomeexpert(self.user_id)

class Guestbook(db.Document):
    #成为审核
    __tablename__ = 'guestbook'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)  # id
    user_id = db.IntField(default=0, db_field='ui')  # 用户ID
    content = db.StringField(default='', db_field='c')  # 留言内容
    name = db.StringField(default='', db_field='n') 
    phone = db.StringField(default='', db_field='p') 
    date = db.IntField(default=0, db_field='d')  # 创建时间

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)
        self.date = common.getstamp()
        self.save()

    @staticmethod
    def getlist(index=1, count=10):
        pageindex =(index-1)*count
        return Guestbook.objects.order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount():
        return Guestbook.objects.count()

class RLYRecord(db.Document):
    #容联云通讯 通话录音
    __tablename__ = 'rlyrecord'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)  # id
    user_id = db.IntField(default=0, db_field='ui') # 用户ID
    action = db.StringField(default='', db_field='a') # 请求类型
    orderid = db.StringField(default='', db_field='o') # 订单id
    subid = db.StringField(default='', db_field='s') # 子账号id
    caller = db.StringField(default='', db_field='cr') # 主叫号码
    called = db.StringField(default='', db_field='cd') # 被叫号码
    starttime = db.IntField(default=0, db_field='st') # 通话开始时间
    endtime = db.IntField(default=0, db_field='et') # 通话结束时间
    recordurl = db.StringField(default='', db_field='ru') # 通话录音完整下载地址
    byetype = db.StringField(default='', db_field='bt') # 通话挂机类型
    date = db.IntField(default=0, db_field='d')  # 创建时间

    def saveinfo(self):
        self._id = collection.get_next_id(self.__tablename__)
        self.date = common.getstamp()
        self.save()

    def updateinfo(self):
        update = {}
        update['set__calltime'] = self.calltime
        RLYRecord.objects(user_id=self.user_id,call_id=self.call_id).update_one(**update)

    @staticmethod
    def getinfo(aid):
        # 获取通讯记录 (orderid)
        return RLYRecord.objects(orderid=aid).first()

    @staticmethod
    def getlist(index=1, count=10):
        pageindex =(index-1)*count
        return RLYRecord.objects.order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount():
        return RLYRecord.objects.count()
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
from . import db,rs, login_manager,searchwhoosh
from core import common
import json
#import cpickle as pickle

class Permission:
    VIEW = 0x01 # 查看
    EDIT = 0x02 # 编辑
    DELETE = 0x04 # 删除
    ADMINISTER = 0x80

class RolePermissions(db.EmbeddedDocument):  # 角色权限
    user = db.IntField(default=0, db_field='u')

    def to_json(self):
        json_rp = {
            'user': self.user
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
		print roles
		for r in roles:
			role = Role()
			role.permissions = roles[r][0]
			role.default = roles[r][1]
			role._id = collection.get_next_id('role')
			role.name = '12@qq.com'
			role.save()
	@staticmethod
	def getlist():
		rv = rs.get(Role.CACHEKEY['list'])
		if rv is None:
			rv = Role.objects().limit(30)
			temp =  json.dumps([item.to_json() for item in rv])
			rs.set(Role.CACHEKEY['list'],temp)
		else:
			rv = json.loads(rv)

		return rv

	def editinfo(self):
		rs.delete(Role.CACHEKEY['list'])
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
		if rid>0:
			rlist = Role.getlist()
			for item in rlist:
				if item['_id']==rid:
					return item
			return None
		else:
			return None

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
    lastaction = db.IntField(default=common.getstamp(), db_field='la')  # 最后更新时间
    rand = db.IntField(default=common.getrandom(), db_field='r')  # 随机数 用于随机获取专家列表
    message_count = 0  # 消息个数

    def to_json(self):
        json_us = {
            'meet': self.meet
        }
        return json_us


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


class User(UserMixin, db.Document):  # 会员
    __tablename__ = 'users'
    meta = {
        'collection': __tablename__,
    }
    _id = db.IntField(primary_key=True)
    email = db.StringField(default='', max_length=64, db_field='e')  # 邮箱
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
    date = db.IntField(default=common.getstamp(), db_field='d')  # 创建时间
    intro = db.StringField(default='', db_field='i')  # 简介
    fileurl = db.StringField(default='', db_field='f')  # 介绍图片或视频地址
    label = db.ListField(default=[], db_field='l')  # 标签
    workexp = db.ListField(
        db.EmbeddedDocumentField(WorkExp), default=[], db_field='we')  # 工作经历
    edu = db.ListField(
        db.EmbeddedDocumentField(Edu), default=[], db_field='ed')  # 教育背景
    state = db.IntField(default=1, db_field='sta')# 状态 1 正常  -1新增  -2待审核 0暂停
    thinktank = db.ListField(default=[], db_field='t')  # 智囊团

    @staticmethod
    def getlist(roid=0,index=1,count=10):
        #.exclude('password_hash') 不包含字段
        pageindex =(index-1)*count
        if roid == 0:
            return User.objects.order_by("-_id").skip(pageindex).limit(count)
        else:
            return User.objects(role_id=roid).order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def getcount(roid=0):
    	if roid == 0:
            return User.objects.count()
        else:
            return User.objects(role_id=roid).count()

    @staticmethod
    def getlist_uid(uidlist, feild=[], count=10):  
        # 获取指定id列表的会员数据
        #.exclude('password_hash') 不包含字段
        return User.objects(_id__in=uidlist).limit(
            count).exclude('password_hash')

    @staticmethod
    def getthinktanklist_uid(uidlist):
        # 获取智囊团列表
        return User.objects(_id__in=uidlist).exclude('password_hash')

    @staticmethod
    def getinfo(uid, feild=[]):  # 获取指定id列表的会员数据
        #.exclude('password_hash') 不包含字段
        return User.objects(_id=uid).exclude('password_hash').first()

    @staticmethod
    def getadmininfo(uid):  # 获取指定id 管理员信息
        #.exclude('password_hash') 不包含字段
        return User.objects(_id=uid,role_id=1).only('name').first()

    @staticmethod
    def getlist_geo_map(x, y,count=10, max=1000):
    	#根据坐标获取数据列表 max最大距离(米)
        return User.objects(geo__near=[x, y],geo__max_distance=max)

    @staticmethod
    def getlist_geo_list(x, y,industryid=0,count=10, max=1000):
    	#根据坐标获取数据列表 max最大距离(米)
    	query = Q(geo__near=[x, y]) & Q(geo__max_distance=max)
    	if industryid>0:
    		query = query & Q(industryid=industryid)
        list_count = User.objects(query).count()
        if list_count>=count:
            rand = common.getrandom()
            relist = []
            u_list = User.objects(query & Q(stats__rand__gte=rand))#)|Q(_id__gte=rand)
            for item in u_list:
		        relist.append(item)
            if len(u_list)<count:
                ul_list = User.objects(query & Q(stats__rand__lte=rand))#|Q(_id__lte=rand)
                for item in ul_list:
		        	relist.append(item)

            return relist
        else:
            return User.objects(query)

    @staticmethod
    def isusername(username):
		#查找帐号是否存在 >0 存在   =0 不存在
		if len(username)>0:
			return User.objects(username=username).count()
		else:
			return -1

    def useredit(self):
    	if self._id > 0:
    		update = {}
    		if self.role_id==1:

	            if len(self.name) > 0:
	                update['set__name'] = self.name
	            update['set__sex'] = self.sex
	            update['set__stats__lastaction'] = common.getstamp()
	            User.objects(_id=self._id).update_one(**update)
	        else:
	        	pass

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
    def updatephone(newphone):
        #更新手机号
        #if g.current_user is not None:
        #    if g.current_user._id > 0:
        update = {}
        update['set__username'] = newphone
        User.objects(_id=23).update_one(**update)
        return 1
        #return 0

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
            if len(self.password_hash) > 0:
                self.password = self.password_hash
                update['set__password_hash'] = self.password_hash
            update['set__confirmed'] = self.confirmed
            update['set__domainid'] = self.domainid
            update['set__industryid'] = self.industryid
            update['set__sex'] = self.sex
            update['set__job'] = self.job
            update['set__geo'] = self.geo
            update['set__intro'] = self.intro
            update['set__fileurl'] = self.fileurl
            update['set__label'] = self.label
            update['set__workexp'] = self.workexp
            update['set__edu'] = self.edu
            update['set__stats__lastaction'] = common.getstamp()
            update['set__state'] = self.state

            User.objects(_id=self._id).update_one(**update)

            #更新whoosh
            updata_whoosh = {}
            updata_whoosh['_id']=self._id
            updata_whoosh['n']=unicode(self.name)
            updata_whoosh['l']=self.label
            updata_whoosh['j']=self.job
            searchwhoosh.update(updata_whoosh)

            Log.saveinfo(remark='编辑用户('+str(self._id)+')')

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
                self.save()

                #更新whoosh
                updata_whoosh = {}
                updata_whoosh['_id']= self._id
                updata_whoosh['n']= unicode(self.name)
                updata_whoosh['j']= unicode(self.job)
                updata_whoosh['l']=self.label
                searchwhoosh.update(updata_whoosh)

                Log.saveinfo(remark='创建用户('+str(self._id)+')')

                return self._id
            else:
                return -1

    @staticmethod
    def list_search(roid,text, count=10):  # 后台搜索
        return User.objects((Q(name__istartswith=text) | Q(job__istartswith=text))&Q(role_id=roid)).limit(count).exclude('password_hash')

    @staticmethod
    def search(text, count=10):  # 专家搜索
        return User.objects(Q(name__istartswith=text) | Q(job__istartswith=text)).limit(count).only('name','job')


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
    '''

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True
    '''

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

    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

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
        if type == 0:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'sex': self.sex,
                'job': self.job.encode('utf-8'),
                'auth': {'vip': 1},  # self.auth.vip
                'grade': common.getgrade(self.stats.comment_count, self.stats.comment_total),
                'meet_c': self.stats.meet,
                # [39.9442, 116.324]
                'geo': [self.geo['coordinates'][1], self.geo['coordinates'][0]],
                'intro': self.intro.encode('utf-8'),
                'fileurl': self.fileurl.encode('utf-8'),
                'avaurl': common.getavatar(userid=self.id),
                'work': [item.to_json() for item in self.workexp],
                'edu': [item.to_json() for item in self.edu],
                'label':self.label,
                'role_id':self.role_id,
                'domainid':self.domainid,
                'industryid':self.industryid
            }
        elif type == 1:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'avaurl': common.getavatar(userid=self.id)
            }
        elif type == 2:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'intro': self.intro.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavatar(userid=self.id)
            }
        elif type == 3:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavatar(userid=self.id)
            }
        elif type == 4:
            json_user = {
                '_id': self.id,
                'name': self.name.encode('utf-8'),
                'job': self.job.encode('utf-8'),
                'avaurl': common.getavatar(userid=self.id),
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
                'avaurl': common.getavatar(userid=self.id),
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
                'avaurl': common.getavatar(userid=self.id),
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
        default='', max_length=100, db_field='b')  # 背景图片地址

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

    @staticmethod
    def getlist(uid=0,index=1, count=10):
    	# 获取列表 0全部  -1官方  -2专家
        uid = int(uid)
        pageindex =(index-1)*count
        if uid == 0:
            return Topic.objects.exclude('content').order_by("-_id").skip(pageindex).limit(count)
        elif uid == -1:
            return Topic.objects(user_id=0).exclude('content').order_by("-_id").skip(pageindex).limit(count)
        elif uid == -2:
            return Topic.objects(user_id__gt=0).exclude('content').order_by("-_id").skip(pageindex).limit(count)
        else:
            return Topic.objects(user_id=uid).exclude('content').order_by("-_id").skip(pageindex).limit(count)

    @staticmethod
    def list_search(uid,text, count=10):  # 后台搜索
        uid = int(uid)
        query = Q(title__istartswith=text)
        if uid == -1 :
            query = query & Q(user_id=0)
        elif uid==-2:
            query = query & Q(user_id__gt=0)
        return Topic.objects(query).limit(count).exclude('content')

    @staticmethod
    def getcount(uid=0):
        uid = int(uid)
    	if uid == 0:
            return Topic.objects.count()
        elif uid == -1:
            return Topic.objects(user_id=0).count()
        elif uid == -2:
            return Topic.objects(user_id__gt=0).count()
        else:
            return Topic.objects(user_id=uid).count()

    @staticmethod
    def getinfo(tid=0):
        return Topic.objects.get(_id=tid)

    @staticmethod
    def getinfo_expert(tid):  # 获取话题的专家id列表(expert字段)
        #.exclude('password_hash') 不包含字段
        return Topic.objects.only('expert').get(_id=tid)

    def editinfo(self):
        if self._id > 0:
            update = {}
            # update.append({'set__email': self.email})

            update['set__user_id'] = self.user_id
            if len(self.title) > 0:
                update['set__title'] = self.title
            if len(self.intro) > 0:
                update['set__intro'] = self.intro
            if len(self.content) > 0:
                update['set__content'] = self.content
            update['set__pay__call'] = self.pay.call
            update['set__pay__meet'] = self.pay.meet
            update['set__pay__calltime'] = self.pay.calltime
            update['set__pay__meettime'] = self.pay.meettime
            update['set__expert'] = self.expert
            update['set__config__background'] = self.config.background

            update['set__stats__topic_count'] = self.stats.topic_count
            update['set__stats__topic_total'] = self.stats.topic_total
            Topic.objects(_id=self._id).update_one(**update)

            Log.saveinfo(remark='编辑话题('+str(self._id)+')')
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            Log.saveinfo(remark='创建话题('+str(self._id)+')')
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
                'expert': [item.to_json(1) for item in User.getlist_uid(uidlist=self.expert, count=4)],
                'stats': self.stats.to_json()
                #'expert': [50, 38, 47, 39]
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
                'expert': [item.to_json(5) for item in User.getlist_uid(uidlist=self.expert, count=4)],
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
                'expert': u_info is not None and u_info.to_json(2) or {},
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
            'avaurl': common.getavatar(userid=self.user_id)
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
    return User.objects(id=user_id)


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
            'expert': [item.to_json(3) for item in User.getlist_uid(uidlist=self.expert, count=4)],
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
    def getlist(count=10):
        return Inventory.objects.exclude('topic').limit(count)

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
            Log.saveinfo(remark='编辑清单('+str(self._id)+')')
            return 1
        else:
            self._id = collection.get_next_id(self.__tablename__)
            self.save()
            Log.saveinfo(remark='创建清单('+str(self._id)+')')
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
    group_id = db.IntField(default=0, required=True, db_field='g')  # 分组id
    fileurl = db.StringField(default='', db_field='fu')  # 文件地址
    url = db.StringField(db_field='u')  # 跳转地址或 跳转id
    sort = db.IntField(default=0, db_field='s')  # 排序

    @staticmethod
    def getlist(gid=0, count=10):
        # .exclude('password_hash') 不包含字段
        return Ad.objects(group_id=gid).limit(count)

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
    apptype = db.IntField(default=1, db_field='at')  # 预约方式 1通话 2见面
    address = db.StringField(default='', db_field='a')  # 预约地址
    price = db.IntField(default=0, db_field='p')  # 支付价格
    attachment = db.ListField(default=[], db_field='att')  # 附件
    remark = db.StringField(default='', db_field='r')  # 备注
    state = db.IntField(default=0, db_field='s')  # 预约状态
    paystate = db.IntField(default=0, db_field='ps')  # 支付状态

    @staticmethod
    # _type=1我约 _type=2被约  /  appid 约/被约 专家id
    def getlist(_type=0, appid=0, count=10):
        if _type == 0:
            return Appointment.objects().limit(count)
        elif _type == 2:
            return Appointment.objects(appid=appid).limit(count)
        elif _type == 1:
            return Appointment.objects(user_id=appid).limit(count)

    @staticmethod
    def getinfo(aid):
        return Appointment.objects(_id=aid).first()

    @staticmethod
    def createid():
        # 生成自增id
        return collection.get_next_id(Appointment.__tablename__)

    def to_json(self, _type=1, type=1):  # type返回相应字段 1列表 0详情
        uinfo = User.getinfo(_type == 2 and self.appid or self.user_id)
        if uinfo is not None:
            if type == 1:
                json_app = {
                    '_id': self.id,
                    'info': uinfo.to_json(3),
                    'user_id': self.user_id,
                    'appid': self.appid,
                    'topic_id': self.topic_id,
                    'topic_title': self.topic_title.encode('utf-8'),
                    'appdate': self.appdate,
                    'apptype': self.apptype,
                    #'address': self.address.encode('utf-8'),
                    'price': self.price,
                    #'attachment': self.attachment,
                    #'remark': self.remark.encode('utf-8'),
                    'state': self.state,
                    'paystate': self.paystate
                }
            else:  # 0
                json_app = {
                    '_id': self.id,
                    'data': int(str(self.id)[0:8], 16),
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
                    'paystate': self.paystate
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
        Log(remark=remark,admin_id=aid==0 and g.current_user._id or aid,_id=collection.get_next_id(Log.__tablename__)).save()

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
    date = db.IntField(default=common.getstamp(), db_field='d')  # 创建时间
    type = db.IntField(default=0, db_field='ty')  # 消息类型
    title = db.StringField(default='', db_field='t')  # 标题
    content = db.StringField(default='', db_field='c')  # 内容

    @staticmethod
    def saveinfo(self):
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
            'user_id': self.user_id,
            'appointment_id': self.appointment_id,
            'date': self.date,
            'type': self.type
        }
        return json_message
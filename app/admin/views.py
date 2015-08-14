#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, flash
from flask import g
from .authentication import auth
from werkzeug import secure_filename
from flask.ext.login import login_required, current_user, logout_user
from . import admin
from .decorators import permission_required
from .forms import EditUserForm,EditTopicForm,EditInventoryForm,EditRoleForm,EditAdForm
from ..models import collection,User,WorkExp,Edu,Role,Permission,Topic,InvTopic,InvTopicStats,Log,Inventory,Appointment,Ad
from .. import q_image,conf#searchwhoosh,rs
from ..sdk import tencentyun
from ..core import common
import logging
import time

'''
@admin.route('/upfile', methods=['POST'])  # , methods=['GET', 'POST']
@auth.login_required
def upfile():
    if request.method == 'POST':
        import os
        

        _type = request.args.get('type', '')
        uid = request.args.get('uid', 0)
        
        if uid>0:
            if _type=='introfile':
                try:
                    file = request.files['file']
                    savepath = common.getuserpath(uid) #存储路径
                    #newpath = 'introfile.'+file.filename.rsplit('.', 1)[1] # 新文件名
                    newpath = 'introfile.jpg'
                    print file+'__________'
                    if file and common.allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        print filename
                        if not os.path.exists(savepath):
                            os.makedirs(savepath)
                        file.save(os.path.join(savepath, newpath))

                        fileid = 'introfile_'+str(uid)
                        q_image.delete(conf.QCLOUD_BUCKET, fileid)
                        print str(g.current_user._id)
                        obj = q_image.upload(os.path.join(savepath, newpath), conf.QCLOUD_BUCKET, fileid);
                        imgwurl = ''
                        if obj['code'] == 0 :
                            #fileid = obj['data']['fileid']
                            imgwurl = obj['data']['download_url']
                            return '{"ret":1,"url":"'+imgwurl+'"}'
                        else:
                            return '{"ret":0}'
                except Exception,e:
                    logging.debug(e)
                    return '{"ret":-1}'#系统异常
    return '{"ret":0}'
'''

@admin.route('/userlist/search/<string:text>', methods=['GET'])
@admin.route('/userlist/search/<int:roid>/<string:text>', methods=['GET'])
@auth.login_required
def user_list_search(text='',roid=2):
    if len(text)>0:
        userlist = User.list_search(roid,text)
        for item in userlist:
            item.role = Role.getinfo(item.role_id)
        func = {'getdomain': common.getdomain,'getindustry': common.getindustry,'stamp2time': common.stamp2time,'getuserstate':common.getuserstate}
        return render_template('admin/user_list.html', userlist=userlist,func=func,roid=roid,text=text,index=-1)


@admin.route('/userlist', methods=['GET', 'POST'])  # , methods=['GET', 'POST']
@admin.route('/userlist/<int:roid>', methods=['GET', 'POST'])
@admin.route('/userlist/<int:roid>/<int:index>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
#@login_required
#@admin_required
#@permission_required(Permission.USER)
@auth.login_required
def user_list(roid=2,index=1):

    if request.method == 'POST':
        _type = request.args.get('type','')
        uid = request.args.get('uid',0,type=int)
        if uid>0:
            if _type=='state':# 审核通过
                User.updatestate(uid,1)
                flash('用户审核通过')
            elif _type=='unstate': # 设为待审核
                User.updatestate(uid,-2)
                flash('用户已下线')
        return redirect(url_for('.user_list',roid=roid))
    else:
    	pagesize = 8
    	count = User.getcount(roid=roid)
    	usercount = common.getpagecount(count,pagesize)
    	if index>usercount:
    		index = usercount
    	if index<1:
    		index=1

        userlist = User.getlist(roid=roid,index=index,count=pagesize)
        for item in userlist:
        	item.role = Role.getinfo(item.role_id)
        func = {'getdomain': common.getdomain,'getindustry': common.getindustry,'stamp2time': common.stamp2time,'getuserstate':common.getuserstate}
        # orig.get(body='Ross19').update({'$rename': {'body_html': 'body_w'}})
        return render_template('admin/user_list.html', userlist=userlist,func=func,roid=roid,pagecount=usercount,index=index)

@admin.route('/useredit', methods=['GET', 'POST'])
@admin.route('/useredit/<int:id>', methods=['GET', 'POST'])
@admin.route('/useredit/<int:id>/<int:roid>', methods=['GET', 'POST'])
@admin.route('/useredit/<int:id>/<int:roid>/<int:pindex>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
@auth.login_required
def user_edit(roid=2,id=0,pindex=1):
    form = EditUserForm()

    #print request.method + "++++++" + str(form.validate())
    if request.method == 'POST' and form.validate_on_submit():

        user = User()
        user._id = id
        user.role_id = roid #request.form.get('roleid',0)
        user.name = form.name.data
        user.username = form.username.data
        user.email = request.form.get('email','')
        if id==0:
            user.password_hash = '123456'
        else:
            user.password_hash = form.password.data
        user.confirmed = 1 #request.form.get('confirmed',1)
        user.domainid = request.form.get('domainid',0)
        user.industryid = request.form.get('industryid',0)
        user.sex = request.form.get('sex',1)
        user.job = request.form.get('job','')
        user.geo = [float(i.strip()) for i in request.form.get('geo','0,0').split(',')]
        user.intro = request.form.get('intro','')
        user.fileurl = request.form.get('fileurl','')
        user.state = -2
        lab = request.form.get('label','')
        if len(lab.strip())>0:
        	user.label = [i.strip() for i in lab.split(',')]
        user.label = common.delrepeat(user.label) #移除标签中重复
        wecount = int(request.form.get('wecount',0))
        welist= []
        for weid in xrange(1, wecount+1):
            newitem = str(weid)
            tempWorkExp = WorkExp()
            tempWorkExp.name = request.form.get('wename_'+newitem,'')
            if len(tempWorkExp.name)>0:
                tempWorkExp.start = common.time2stamp(request.form.get('westart_'+newitem,0),'%Y-%m-%d')
                tempWorkExp.end = common.time2stamp(request.form.get('weend_'+newitem,0),'%Y-%m-%d')
                tempWorkExp.job = request.form.get('wejob_'+newitem,'')
                #tempWorkExp.intro = request.form.get('weintro_'+newitem,'')
            	welist.append(tempWorkExp)
        user.workexp = welist
        educount = int(request.form.get('educount',0))
        edulist =[]
        for eduid in xrange(1, educount+1):
            newitem = str(eduid)
            tempedu = Edu()
            tempedu.name = request.form.get('eduname_'+newitem,'')
            if len(tempedu.name)>0:
                tempedu.start = common.time2stamp(request.form.get('edustart_'+newitem,0),'%Y-%m-%d')
                tempedu.end = common.time2stamp(request.form.get('eduend_'+newitem,0),'%Y-%m-%d')
                tempedu.dip = request.form.get('edudip_'+newitem,'')
                tempedu.major = request.form.get('edumajor_'+newitem,'')
            	edulist.append(tempedu)
        user.edu = edulist
        user.editinfo()
        #flash('用户更新成功','error')
        return redirect(url_for('.user_list',roid=roid,index=pindex))
    else:
        isuser = False
        user = None
        rolelist = Role.getlist()
        sign=''
        if id > 0 :
            q_auth = tencentyun.Auth(conf.QCLOUD_SECRET_ID,conf.QCLOUD_SECRET_KEY)
            expired = int(time.time()) + 999
            sign = q_auth.get_app_sign_v2(bucket=conf.QCLOUD_BUCKET, fileid='introfile_'+str(id),expired=expired)
            user = User.getinfo(id)
            if user:
                isuser = True
        func = {'stamp2time': common.stamp2time,'len': len}
        return render_template('admin/user_edit.html',roid=roid, user=user, isuser=isuser, form=form,func=func,rolelist=rolelist,DOMAIN=conf.DOMAIN,INDUSTRY=conf.INDUSTRY,sign=sign,pindex=pindex)

@admin.route('/logout')
@auth.login_required
def logout():
    logout_user()
    return jsonify(msg='用户已登出')

@admin.route('/pluginlist', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
#@login_required
#@admin_required
#@permission_required(Permission.USER)
@auth.login_required
def plugin_list():
    if request.method == 'POST':
        rebuild = request.args.get('rebuild', 0, type=int)
        if rebuild==1:
            pass
            #重新生成whoosh
            #searchwhoosh.rebuild_index()
        elif rebuild==2:
            pass
            #清空redis缓存
            #rs.flushdb()
        return redirect(url_for('.plugin_list'))
    else:

        return render_template('admin/plugin_list.html',size=0)#rs.dbsize()

@admin.route('/topiclist/search/<string:text>', methods=['GET'])
@auth.login_required
def user_topiclist_search(text=''):
    if len(text)>0:
        topiclist = Topic.list_search(-2,text)
        func = {'stamp2time': common.stamp2time}
        return render_template('admin/topic_list.html', topiclist=topiclist,func=func,uid=-2,text=text,index=-1)

@admin.route('/topicteamlist/search/<string:text>', methods=['GET'])
@auth.login_required
def user_topicteamlist_search(text=''):
    if len(text)>0:
        topiclist = Topic.list_search(-1,text)
        func = {'stamp2time': common.stamp2time}
        return render_template('admin/topicteam_list.html', topiclist=topiclist,func=func,uid=-1,text=text,index=-1)


@admin.route('/topiclist',methods=['GET', 'POST'])
@admin.route('/topiclist/<string:uid>', methods=['GET', 'POST'])
@admin.route('/topiclist/<string:uid>/<int:index>', methods=['GET', 'POST'])
@auth.login_required
def topic_list(uid=-2,index=1):
    if request.method == 'POST':
        return redirect(url_for('.topic_list'))
    else:
    	pagesize = 8
    	count = Topic.getcount(uid)
    	tpcount = common.getpagecount(count,pagesize)
    	if index>tpcount:
    		index = tpcount
    	if index<1:
    		index=1
        topiclist = Topic.getlist(uid=uid,index=index,count=pagesize)
        func = {'stamp2time': common.stamp2time}

        return render_template('admin/topic_list.html',topiclist=topiclist, func=func,uid=uid,pagecount=tpcount,index=index)

@admin.route('/topicteamlist',methods=['GET', 'POST'])
@admin.route('/topicteamlist/<string:uid>', methods=['GET', 'POST'])
@admin.route('/topicteamlist/<string:uid>/<int:index>', methods=['GET', 'POST'])
@auth.login_required
def topicteam_list(uid=-1,index=1):
    if request.method == 'POST':
        return redirect(url_for('.topic_list'))
    else:
        pagesize = 8
        count = Topic.getcount(uid)
        tpcount = common.getpagecount(count,pagesize)
        if index>tpcount:
            index = tpcount
        if index<1:
            index=1
        topiclist = Topic.getlist(uid=-1,index=index,count=pagesize)
        func = {'stamp2time': common.stamp2time}
        return render_template('admin/topicteam_list.html',topiclist=topiclist, func=func,uid=uid,pagecount=tpcount,index=index)

@admin.route('/topicedit', defaults={'id': 0}, methods=['GET', 'POST'])
@admin.route('/topicedit/<int:id>/<int:_type>', methods=['GET', 'POST'])
@admin.route('/topicedit/<int:id>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
@auth.login_required
def topic_edit(id,_type=0):
    form = EditTopicForm()
    if request.method == 'POST' and form.validate_on_submit():

        topic = Topic()
        topic._id = id
        topic.user_id = form.eid.data
        topic.title = form.title.data
        topic.intro = form.intro.data
        topic.content = form.content.data
        topic.pay.call = form.call.data
        topic.pay.meet = form.meet.data
        '''
        tempexp = form.expert.data
        if len(tempexp)>0:
            topic.expert = [int(i.strip()) for i in tempexp.split(',')]
        topic.config.background = form.background.data
        '''
        topic.stats.topic_count = form.topic_count.data
        topic.stats.topic_total = form.topic_total.data
        topic.sort = request.form.get('sort',0)
        topic.editinfo()

        return redirect(url_for(_type==0 and '.topic_list' or '.user_list'))
    else:
        istopic = False
        topic = None
        uid = 0
        if _type==1:
            uid = id
        elif id > 0 :
            topic = Topic.getinfo(id)
            if topic:
                istopic = True
        return render_template('admin/topic_edit.html', topic=topic,_type=_type, istopic=istopic,uid=uid, form=form)

@admin.route('/topicteamedit', defaults={'id': 0}, methods=['GET', 'POST'])
@admin.route('/topicteamedit/<int:id>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
@auth.login_required
def topicteam_edit(id):
    form = EditTopicForm()
    if request.method == 'POST' and form.validate_on_submit():

        topic = Topic()
        topic._id = id
        topic.user_id = 0
        topic.title = form.title.data
        topic.intro = form.intro.data
        topic.content = form.content.data
        #topic.pay.call = form.call.data
        #topic.pay.meet = form.meet.data
        tempexp = form.expert.data
        if len(tempexp)>0:
            topic.expert = [int(i.strip()) for i in tempexp.split(',')]
        topic.config.background = form.background.data
        #topic.stats.topic_count = form.topic_count.data
        #topic.stats.topic_total = form.topic_total.data
        topic.sort = request.form.get('sort',0)
        topic.editinfo()
        return redirect(url_for('.topicteam_list'))
    else:
        istopic = False
        topic = None
        if id > 0 :
            topic = Topic.getinfo(id)
            if topic:
                istopic = True
        return render_template('admin/topicteam_edit.html', topic=topic, istopic=istopic, form=form)

@admin.route('/inventorylist', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
#@login_required
#@admin_required
#@permission_required(Permission.USER)
@auth.login_required
def inventory_list():
    if request.method == 'POST':
        return redirect(url_for('.inventory_list'))
    else:
        inventorylist = Inventory.getlist()
        func = {'stamp2time': common.stamp2time}
        return render_template('admin/inventory_list.html',inventorylist=inventorylist, func=func)


@admin.route('/inventoryedit', defaults={'iid': 0}, methods=['GET', 'POST'])
@admin.route('/inventoryedit/<int:iid>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
@auth.login_required
def inventory_edit(iid):
    form = EditInventoryForm()
    if request.method == 'POST' and form.validate_on_submit():
        inv = Inventory()
        inv.title = form.title.data
        inv.sort = form.sort.data
        if iid>0:
            tempinv = Inventory.getinfo(iid)
            inv._id = iid
            for item in tempinv.topic:
                tempInvTopic = InvTopic()
                tempid = str(item._id)
                tempInvTopic.title = request.form.get('title_'+tempid,'')
                if len(tempInvTopic.title)>0:
                    tempInvTopic._id = item._id
                    tempInvTopic.content = request.form.get('content_'+tempid,'')
                    tempInvTopic.expert = [int(i.strip()) for i in request.form.get('expert_'+tempid,'').split(',')]
                    tempInvTopic.sort = int(request.form.get('sort_'+tempid,'').strip())
                    tempInvTopicStats = InvTopicStats()
                    tempInvTopicStats.like=int(request.form.get('like_'+tempid,'').strip())
                    tempInvTopic.stats = tempInvTopicStats

                    inv.topic.append(tempInvTopic)

        newcount = int(request.form.get('newcount',0))
        for newid in xrange(1, newcount+1):
            newitem = str(newid)
            tempInvTopic = InvTopic()
            tempInvTopic.title = request.form.get('newtitle_'+newitem,'')
            if len(tempInvTopic.title)>0:
                tempInvTopic._id = collection.get_next_id('invtopic')
                tempInvTopic.content = request.form.get('newcontent_'+newitem,'')
                tempInvTopic.expert = [int(i.strip()) for i in request.form.get('newexpert_'+newitem,'').split(' ')]
                tempInvTopic.sort = int(request.form.get('newsort_'+newitem,'').strip())
                tempInvTopicStats = InvTopicStats()
                tempInvTopicStats.like=int(request.form.get('newlike_'+newitem,'').strip())
                tempInvTopic.stats = tempInvTopicStats

                inv.topic.append(tempInvTopic)

        inv.editinfo()
        return redirect(url_for('.inventory_list'))
    else:

        isinv = False
        inv = None
        if iid > 0 :
            inv = Inventory.getinfo(iid)
            if inv:
                isinv = True
        return render_template('admin/inventory_edit.html', inventory=inv, isinventory=isinv, form=form)



@admin.route('/appointmentlist', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
#@login_required
#@admin_required
#@permission_required(Permission.USER)
@auth.login_required
def appointment_list():
    if request.method == 'POST':
        return redirect(url_for('.appointment_list'))
    else:
        inventorylist = Appointment.getlist()
        func = {'stamp2time': common.stamp2time}
        return render_template('admin/appointment_list.html',inventorylist=inventorylist, func=func)

@admin.route('/rolelist', methods=['GET', 'POST'])
@auth.login_required
def role_list():
    if request.method == 'POST':
        return redirect(url_for('.role_list'))
    else:
        rolelist = Role.getlist()
        return render_template('admin/role_list.html',rolelist=rolelist)

@admin.route('/roleedit', defaults={'rid': 0}, methods=['GET', 'POST'])
@admin.route('/roleedit/<int:rid>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
@auth.login_required
def role_edit(rid):
    form = EditRoleForm()
    if request.method == 'POST' and form.validate_on_submit():
        r_edit = Role()
        r_edit._id = rid
        r_edit.name = form.name.data
        r_edit.default = form.default.data is 1 and True or False

        tempperarr = request.form.getlist('user')
        temp_per = 0
        for item in tempperarr:
            temp_per=temp_per|int(item)
        r_edit.permissions.user = temp_per
        r_edit.editinfo()
        return redirect(url_for('.role_list'))
    else:
        #Role.insert_roles()
        isrole = False
        role = None

        if rid > 0 :
            role = Role.getinfo(rid)
            if role:
                isrole = True
        func = {'can': common.can}
        return render_template('admin/role_edit.html', role=role, isrole=isrole, form=form,Permission=Permission,func=func)

@admin.route('/loglist', defaults={'index': 0},methods=['GET', 'POST'])
@admin.route('/loglist/<int:aid>', methods=['GET', 'POST'])
@admin.route('/loglist/<int:aid>/<int:index>', methods=['GET', 'POST'])
@auth.login_required
def log_list(aid=0,index=1):
    if request.method == 'POST':
        return redirect(url_for('.log_list'))
    else:
        pagesize = 8
        count = Log.getcount()
        lcount = common.getpagecount(count,pagesize)
        if index>lcount:
            index = lcount
        if index<1:
            index=1
        loglist = Log.getlist(aid=0,index=index,count=pagesize)

        func = {'stamp2time': common.stamp2time}
        return render_template('admin/log_list.html',loglist=loglist,getadmininfo=User.getadmininfo, func=func,aid=aid,pagecount=lcount,index=index)

@admin.route('/adlist', methods=['GET', 'POST'])
@auth.login_required
def ad_list():
    if request.method == 'POST':
        return redirect(url_for('.ad_list'))
    else:
        adlist = Ad.getlist()
        func = {'stamp2time': common.stamp2time}
        return render_template('admin/ad_list.html',adlist=adlist, func=func)

@admin.route('/adedit', methods=['GET', 'POST'])
@admin.route('/adedit/<int:id>', methods=['GET', 'POST'])
#@permission_required(Permission.LIST_USER)
@auth.login_required
def ad_edit(id=0):
    form = EditAdForm()
    if request.method == 'POST' and form.validate_on_submit():
        
        ad = Ad()
        ad._id = id
        ad.title = form.title.data
        ad.group_id = request.form.get('group_id',0)
        ad.fileurl = request.form.get('fileurl','')
        ad.url = request.form.get('url','')
        ad.sort = request.form.get('sort',0)
        ad.editinfo()

        return redirect(url_for('.ad_list'))
    else:
        isad = False
        ad = None
        sign=''
        if id > 0 :
            ad = Ad.getinfo(id)
            if ad:
                isad = True

            q_auth = tencentyun.Auth(conf.QCLOUD_SECRET_ID,conf.QCLOUD_SECRET_KEY)
            expired = int(time.time()) + 999
            sign = q_auth.get_app_sign_v2(bucket=conf.QCLOUD_BUCKET, fileid='ad_'+str(id),expired=expired)

        return render_template('admin/ad_edit.html', ad=ad, isad=isad, form=form,sign=sign)
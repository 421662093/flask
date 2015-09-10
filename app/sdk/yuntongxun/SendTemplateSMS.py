#-*- coding: UTF-8 -*-
from CCPRestSDK import REST
import ConfigParser
from ... import conf

accountSid= conf.YUNTONGXUN_SID 
#说明：主账号，登陆云通讯网站后，可在"控制台-应用"中看到开发者主账号ACCOUNT SID。

accountToken= conf.YUNTONGXUN_TOKEN
#说明：主账号Token，登陆云通讯网站后，可在控制台-应用中看到开发者主账号AUTH TOKEN。

appId=conf.YUNTONGXUN_APPID; 
#说明：应用Id，如果是在沙盒环境开发，请配置"控制台-应用-测试DEMO"中的APPID。
#如切换到生产环境，请使用自己创建应用的APPID.

serverIP='sandboxapp.cloopen.com';
#说明：请求地址。沙盒环境配置成sandboxapp.cloopen.com，生产环境配置成app.cloopen.com。

serverPort='8883'; 
#说明：请求端口 ，无论生产环境还是沙盒环境都为8883.

softVersion='2013-12-26'; #说明：REST API版本号保持不变。 

def sendTemplateSMS(to,datas,tempId): 
    #初始化REST SDK
    rest = REST(serverIP,serverPort,softVersion) 
    rest.setAccount(accountSid,accountToken) 
    rest.setAppId(appId)

    result = rest.sendTemplateSMS(to,datas,tempId) 
    #print str(type(result['statusCode']))
    return result['statusCode']
    '''
    for k,v in result.iteritems():
        print k
        if k=='templateSMS' : 
            for k,s in v.iteritems():
                print u'%s:%s' % (k, s) 
        else:
            print u'%s:%s' % (k, v) 
    '''
#-*- coding: UTF-8 -*-  

from CCPRestSDK import REST
import ConfigParser
from ... import conf

accountSid= conf.YUNTONGXUN_SID
#说明：主账号，登陆云通讯网站后，可在"控制台-应用"中看到开发者主账号ACCOUNT SID。

accountToken= conf.YUNTONGXUN_TOKEN; 
#说明：主账号Token，登陆云通讯网站后，可在控制台-应用中看到开发者主账号AUTH TOKEN。

appId= conf.YUNTONGXUN_APPID; 
#说明：应用Id，如果是在沙盒环境开发，请配置"控制台-应用-测试DEMO"中的APPID。
#如切换到生产环境，请使用自己创建应用的APPID.

#请求地址，格式如下，不需要写http://
serverIP='sandboxapp.cloopen.com';

#请求端口
serverPort='8883';

#REST版本号
softVersion='2013-12-26';

 # 创建子帐号
 # @param friendlyName 子帐号名称
def CreateSubAccount(accountName):

    #初始化REST SDK
    rest = REST(serverIP,serverPort,softVersion)
    rest.setAccount(accountSid,accountToken)
    rest.setAppId(appId)

    result = rest.CreateSubAccount(accountName)
    account = []
    for k,v in result.iteritems():

        if k=='SubAccount' :
            #for m in v:
                for k,s in v.iteritems():
                    if k=='voipAccount' or k=='subAccountSid' or k=='voipPwd' or k=='subToken':
                        account.append({k:s})
                    #print '%s:%s' % (k, s)
        else:
            pass
            #account.append({k:v})
            #print '%s:%s' % (k, v)
    #print account
    return account

#CreateSubAccount('子帐号名称')
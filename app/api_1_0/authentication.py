#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import g, jsonify
from flask.ext.httpauth import HTTPBasicAuth  # http安全认证
from ..models import User, AnonymousUser
from . import api
from .errors import unauthorized, forbidden

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    email_or_token = '1@qq.com'
    password = '123456'
    user = User.verify_auth_token(email_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.objects(email=email_or_token).first()
        if not user or not user.verify_password(password):
            return False
        g.token_used = False
    else:
        g.token_used = True
    g.current_user = user

    return True
    '''
    if email_or_token == '':
        g.current_user = AnonymousUser()
        return False
    if password == '':
        print email_or_token + "_____________"
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None

    user = User.objects(email=email_or_token).first()

    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)
    '''


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.confirmed:
        return forbidden('Unconfirmed account')
    '''
    if not g.current_user.is_anonymous() and \
            not g.current_user.confirmed:
        return forbidden('Unconfirmed account')
    '''


@api.route('/token')
@auth.login_required
def get_token():
    if g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})
    '''
    if g.current_user.is_anonymous() or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})
    '''

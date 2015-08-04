from flask import Blueprint

api = Blueprint('api', __name__)

from . import authentication, discovery, errors, pay, expert, user, sys

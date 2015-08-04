from flask import Blueprint

core = Blueprint('core', __name__)

from . import wxpayapi, common, tasks,search

from flask import Blueprint
from flask_restful import Api

bp = Blueprint('api_v1', __name__)
api = Api(bp)

from app.api.v1 import routes

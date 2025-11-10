from flask import Blueprint

bp = Blueprint('groups', __name__, template_folder='templates')

from app.groups import routes
from flask import Blueprint
bp = Blueprint('categories', __name__, url_prefix='/categories')

from app.categories import routes

from flask import Blueprint

bp = Blueprint('expenses', __name__, template_folder='templates')

from app.expenses import routes
from flask import Blueprint

trains_bp = Blueprint("trains", __name__)

from . import routes  # noqa: E402,F401

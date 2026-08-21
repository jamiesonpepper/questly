from flask import Blueprint, Response, g, jsonify, redirect, render_template, url_for

from ..db import get_db
from ..models import has_any_parent, list_kids

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    db = get_db()
    if not has_any_parent(db):
        return redirect(url_for("auth.setup"))
    if g.user:
        return redirect(url_for("parent.dashboard") if g.user["role"] == "parent"
                        else url_for("kid.home"))
    return redirect(url_for("public.who"))


@bp.get("/who")
def who():
    db = get_db()
    if not has_any_parent(db):
        return redirect(url_for("auth.setup"))
    return render_template("auth/who.html", kids=list_kids(db))


@bp.get("/favicon.ico")
def favicon():
    """Browsers ask for this regardless of the <link> tag; answer it so the
    logs stay clean."""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           '<text y=".9em" font-size="90">\u2b50</text></svg>')
    return Response(svg, mimetype="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@bp.get("/healthz")
def healthz():
    try:
        get_db().command("ping")
    except Exception as exc:  # pragma: no cover - surfaced to docker healthcheck
        return jsonify(status="degraded", mongo=str(exc)), 503
    return jsonify(status="ok")

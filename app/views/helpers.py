"""Route guards shared by the blueprints."""

from functools import wraps

from flask import current_app, flash, g, redirect, url_for


def parent_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("auth.parent_login"))
        if g.user["role"] != "parent":
            flash("That's a grown-up page!", "warn")
            return redirect(url_for("kid.home"))
        return view(*args, **kwargs)
    return wrapped


def kid_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("public.who"))
        if g.user["role"] != "kid":
            return redirect(url_for("parent.dashboard"))
        return view(*args, **kwargs)
    return wrapped


def safe_next(default):
    """Return the form's `next` target, but only if it's a path on this site.
    Stops a crafted form from bouncing a signed-in parent off to another host."""
    from flask import request
    target = request.form.get("next", "")
    if target.startswith("/") and not target.startswith("//"):
        return target
    return default


def local_now():
    from datetime import datetime
    return datetime.now(current_app.config["TZINFO"])


def as_int(value, default=0, low=None, high=None):
    try:
        out = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if low is not None:
        out = max(low, out)
    if high is not None:
        out = min(high, out)
    return out

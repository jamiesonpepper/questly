from flask import (Blueprint, flash, g, redirect, render_template, session,
                   url_for)

from ..db import get_db
from ..models import (claim_quest, get_quest, get_reward, history_for,
                      list_rewards, quests_for_kid, redeem, redemptions_for)
from .helpers import kid_required, local_now

bp = Blueprint("kid", __name__, url_prefix="/me")


@bp.get("/")
@kid_required
def home():
    db = get_db()
    kid = g.user
    quests = quests_for_kid(db, kid, local_now())
    rewards = list_rewards(db)

    # The cheapest reward they can't afford yet, to show a progress bar.
    balance = kid.get("points", 0)
    next_up = next((r for r in rewards if r["cost"] > balance), None)
    affordable = [r for r in rewards if r["cost"] <= balance]

    return render_template(
        "kid/home.html",
        kid=kid,
        quests=quests,
        open_quests=[q for q in quests if q["state"] == "open"],
        next_up=next_up,
        affordable=affordable,
        history=history_for(db, kid["_id"], limit=8),
    )


@bp.get("/shop")
@kid_required
def shop():
    db = get_db()
    return render_template(
        "kid/shop.html",
        kid=g.user,
        rewards=list_rewards(db),
        pending=[r for r in redemptions_for(db, g.user["_id"], limit=20)
                 if r["status"] == "pending"],
    )


@bp.post("/shop/<reward_id>/buy")
@kid_required
def buy(reward_id):
    db = get_db()
    reward = get_reward(db, reward_id)
    if not reward or not reward.get("active"):
        flash("That reward isn't available.", "error")
        return redirect(url_for("kid.shop"))

    _, error = redeem(db, g.user, reward)
    if error:
        flash(error, "error")
    else:
        session["celebrate"] = f"You got {reward['title']}! Ask a grown-up to hand it over."
    return redirect(url_for("kid.shop"))


@bp.post("/quests/<quest_id>/done")
@kid_required
def finish_quest(quest_id):
    db = get_db()
    quest = get_quest(db, quest_id)
    if not quest or not quest.get("active"):
        flash("That quest has gone away.", "error")
        return redirect(url_for("kid.home"))

    assigned = quest.get("assigned_to") or []
    if assigned and g.user["_id"] not in assigned:
        flash("That quest isn't yours.", "error")
        return redirect(url_for("kid.home"))

    _, error = claim_quest(db, quest, g.user, local_now())
    if error:
        flash(error, "warn")
    else:
        session["celebrate"] = f"Nice one! {quest['points']} points on the way once it's checked."
    return redirect(url_for("kid.home"))


@bp.get("/stuff")
@kid_required
def stuff():
    db = get_db()
    return render_template(
        "kid/stuff.html",
        kid=g.user,
        history=history_for(db, g.user["_id"], limit=100),
        redemptions=redemptions_for(db, g.user["_id"], limit=50),
    )

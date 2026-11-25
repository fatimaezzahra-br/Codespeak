import os
import re
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from markupsafe import Markup, escape
from sqlalchemy import func, or_

import ai_service
from config import Config
from models import Exercise, GrammarIssue, Submission, User, db

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db.init_app(app)
with app.app_context():
    db.create_all()

SITUATIONS = {
    "client_presentation": ("Client Presentation", "Pitching AI/ERP architecture to executive board."),
    "bug_explanation": ("Bug Explanation", "Root cause analysis & post-mortem technical brief."),
    "job_interview": ("Job Interview", "Tech Lead / Data Engineer technical interview scenario."),
}
LEVELS = ["A2", "B1", "B2", "C1"]


# ---------------------------------------------------------------- utilitaires
def level_from_score(score):
    if score >= 8.5:
        return "C1"
    if score >= 8.0:
        return "B2+"
    if score >= 6.5:
        return "B2"
    if score >= 5:
        return "B1"
    return "A2"


@app.template_filter("fdate")
def fdate(d):
    if not d:
        return ""
    today = datetime.utcnow().date()
    if d.date() == today:
        return "Aujourd'hui, " + d.strftime("%H:%M")
    if d.date() == today - timedelta(days=1):
        return "Hier, " + d.strftime("%H:%M")
    return d.strftime("%d/%m/%Y")


def highlight(text, issues, vocab):
    """Surligne les erreurs (rouge) et le vocabulaire technique (vert)."""
    kinds = {}
    for i in issues:
        p = (i.original or "").strip(" .…")
        if p:
            kinds[p.lower()] = "err"
    for v in vocab:
        kinds.setdefault(v.lower(), "voc")
    if not kinds:
        return escape(text)
    pattern = re.compile("|".join(re.escape(k) for k in sorted(kinds, key=len, reverse=True)), re.I)
    css = {"err": "bg-red-100 text-red-700 rounded px-1",
           "voc": "bg-emerald-100 text-emerald-800 rounded px-1 font-mono text-[13px]"}
    out, pos = [], 0
    for m in pattern.finditer(text):
        out.append(escape(text[pos:m.start()]))
        out.append(Markup('<mark class="{}">{}</mark>').format(css[kinds[m.group(0).lower()]], m.group(0)))
        pos = m.end()
    out.append(escape(text[pos:]))
    return Markup("").join(out)


def login_required(role=None):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not g.user:
                return redirect(url_for("login"))
            if role and g.user.role != role:
                flash("Cette page n'est pas disponible pour votre profil.", "error")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return wrapper
    return deco


@app.before_request
def load_user():
    uid = session.get("user_id")
    g.user = db.session.get(User, uid) if uid else None


@app.context_processor
def inject_globals():
    return dict(user=g.user, level_from_score=level_from_score)


# ---------------------------------------------------------------- authentification
@app.route("/")
def home():
    if not g.user:
        return redirect(url_for("login"))
    return redirect(url_for("teacher_dashboard" if g.user.role == "teacher" else "exercises"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        profile = request.form.get("profile")
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash("Email ou mot de passe incorrect.", "error")
        elif profile and profile != u.role:
            flash("Ce compte ne correspond pas au profil sélectionné.", "error")
        else:
            session.clear()
            session["user_id"] = u.id
            return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- enseignant
@app.route("/teacher/dashboard")
@login_required("teacher")
def teacher_dashboard():
    flt = request.args.get("filter", "all")
    search = request.args.get("q", "").strip()
    now = datetime.utcnow()

    n_students = User.query.filter_by(role="student").count()
    n_active = Exercise.query.filter_by(is_active=True).count()
    n_week = Exercise.query.filter(Exercise.created_at >= now - timedelta(days=7)).count()
    subs = Submission.query.all()
    avg = db.session.query(func.avg(Submission.score_global)).scalar() or 0
    rates = [len(s.found_list) / (len(s.found_list) + len(s.missed_list))
             for s in subs if s.found_list or s.missed_list]
    expected = max(1, n_active * n_students)
    stats = dict(
        n_active=n_active, n_week=n_week, n_subs=len(subs), avg=round(avg, 1),
        return_rate=min(100, round(100 * len(subs) / expected)),
        vocab=round(100 * sum(rates) / len(rates)) if rates else 0,
        n_students=n_students,
    )

    base = (Submission.query.join(User, Submission.student_id == User.id)
            .join(Exercise, Submission.exercise_id == Exercise.id))
    counts = {
        "all": base.count(),
        "a_evaluer": base.filter(Submission.status == "a_evaluer").count(),
        "evalue": base.filter(Submission.status == "evalue").count(),
    }
    q = base
    if flt in ("a_evaluer", "evalue"):
        q = q.filter(Submission.status == flt)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(User.full_name.ilike(like), Exercise.title.ilike(like)))
    rows = q.order_by(Submission.created_at.desc()).limit(50).all()
    recent = Exercise.query.order_by(Exercise.created_at.desc()).limit(3).all()

    return render_template("teacher_dashboard.html", stats=stats, rows=rows, counts=counts,
                           flt=flt, search=search, recent=recent, n_students=n_students,
                           situations=SITUATIONS, levels=LEVELS)


@app.post("/teacher/exercises")
@login_required("teacher")
def create_exercise():
    title = request.form.get("title", "").strip()
    situation = request.form.get("situation", "client_presentation")
    level = request.form.get("level", "B2")
    duration = request.form.get("duration", 90, type=int)
    keywords = [k.strip() for k in request.form.get("keywords", "").split(",") if k.strip()]
    if not title:
        flash("Le titre du scénario est obligatoire.", "error")
        return redirect(url_for("teacher_dashboard"))
    if situation not in SITUATIONS or level not in LEVELS:
        abort(400)
    ex = Exercise(title=title, situation=situation, level=level,
                  duration=max(30, min(180, duration)), keywords=",".join(keywords),
                  instructions=request.form.get("instructions", "").strip(),
                  created_by=g.user.id)
    db.session.add(ex)
    db.session.flush()
    ex.code = f"MGSI-ENG-{ex.id:03d}"
    db.session.commit()
    flash(f"Exercise « {title} » published for the entire class.", "ok")
    return redirect(url_for("teacher_dashboard"))


@app.post("/teacher/exercises/<int:ex_id>/toggle")
@login_required("teacher")
def toggle_exercise(ex_id):
    ex = db.get_or_404(Exercise, ex_id)
    ex.is_active = not ex.is_active
    db.session.commit()
    return redirect(request.referrer or url_for("exercises"))


@app.post("/teacher/submissions/<int:sub_id>/review")
@login_required("teacher")
def review(sub_id):
    s = db.get_or_404(Submission, sub_id)
    s.teacher_comment = request.form.get("comment", "").strip()
    final = request.form.get("final_score", type=float)
    if final is not None and 0 <= final <= 10:
        s.score_global = round(final, 1)
    s.status = "evalue"
    db.session.commit()
    flash("Evaluation saved.", "ok")
    return redirect(url_for("feedback", sub_id=s.id))


# ---------------------------------------------------------------- exercices
@app.route("/exercises")
@login_required()
def exercises():
    q = Exercise.query
    if g.user.role == "student":
        q = q.filter_by(is_active=True)
    items = q.order_by(Exercise.created_at.desc()).all()
    done = {}
    if g.user.role == "student":
        for s in Submission.query.filter_by(student_id=g.user.id).all():
            done[s.exercise_id] = max(done.get(s.exercise_id, 0), s.score_global or 0)
    return render_template("exercises.html", items=items, done=done, situations=SITUATIONS)


@app.route("/exercises/<int:ex_id>")
@login_required()
def exercise_detail(ex_id):
    ex = db.get_or_404(Exercise, ex_id)
    if g.user.role == "student" and not ex.is_active:
        abort(404)
    return render_template("exercise_detail.html", ex=ex, situations=SITUATIONS)


@app.post("/exercises/<int:ex_id>/submit")
@login_required("student")
def submit(ex_id):
    ex = db.get_or_404(Exercise, ex_id)
    duration = int(float(request.form.get("duration", 0) or 0))
    transcript = (request.form.get("transcript") or "").strip()
    filename = None
    audio = request.files.get("audio")
    if audio and audio.filename:
        filename = f"{g.user.id}_{int(time.time())}.webm"
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        audio.save(path)
        if not transcript:
            transcript = ai_service.transcribe(path)
    if len(transcript.split()) < 5:
        return jsonify(error="Transcription vide ou trop courte. Parle plus longtemps ou écris ton texte."), 400

    r = ai_service.analyze(transcript, ex, duration)
    sub = Submission(
        exercise_id=ex.id, student_id=g.user.id, audio_filename=filename,
        duration=r["duration"], transcript=transcript, wpm=r["wpm"],
        fluency=r["fluency"], technical_precision=r["technical_precision"],
        grammar=r["grammar"], pronunciation=r["pronunciation"],
        score_global=r["score_global"], vocab_found=",".join(r["found"]),
        vocab_missed=",".join(r["missed"]), fillers=r["fillers"],
        suggestion=r["suggestion"], status="a_evaluer",
    )
    for i in r["issues"]:
        sub.issues.append(GrammarIssue(
            category=i.get("category"), original=i.get("original"),
            correction=i.get("correction"), explanation=i.get("explanation"),
            priority=i.get("priority")))
    db.session.add(sub)
    db.session.commit()
    return jsonify(url=url_for("feedback", sub_id=sub.id))


# ---------------------------------------------------------------- feedback
@app.route("/feedback")
@login_required()
def feedback_latest():
    q = Submission.query
    if g.user.role == "student":
        q = q.filter_by(student_id=g.user.id)
    s = q.order_by(Submission.created_at.desc()).first()
    if not s:
        return render_template("empty.html", message="No recordings available yet.")
    return redirect(url_for("feedback", sub_id=s.id))


@app.route("/feedback/<int:sub_id>")
@login_required()
def feedback(sub_id):
    s = db.get_or_404(Submission, sub_id)
    if g.user.role == "student" and s.student_id != g.user.id:
        abort(403)
    paragraphs = [highlight(p, s.issues, s.found_list)
                  for p in (s.transcript or "").split("\n\n") if p.strip()]
    return render_template("feedback.html", s=s, paragraphs=paragraphs)


@app.route("/audio/<path:filename>")
@login_required()
def audio(filename):
    s = Submission.query.filter_by(audio_filename=filename).first_or_404()
    if g.user.role == "student" and s.student_id != g.user.id:
        abort(403)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ---------------------------------------------------------------- progression
@app.route("/progress")
@login_required()
def progress():
    students = []
    if g.user.role == "teacher":
        students = User.query.filter_by(role="student").order_by(User.full_name).all()
        sid = request.args.get("student_id", type=int)
        if not sid:
            with_subs = [st for st in students if Submission.query.filter_by(student_id=st.id).first()]
            sid = (with_subs or students or [None])[0]
            sid = sid.id if sid else None
        student = db.session.get(User, sid) if sid else None
    else:
        student = g.user
    if not student:
        return render_template("empty.html", message="No students found.")

    subs = (Submission.query.filter_by(student_id=student.id)
            .order_by(Submission.created_at.asc()).all())
    scored = [s.score_global for s in subs if s.score_global is not None]
    avg = round(sum(scored) / len(scored), 1) if scored else 0

    def crit(attr):
        vals = [getattr(s, attr) for s in subs if getattr(s, attr) is not None]
        if not vals:
            return dict(avg=0, delta=0)
        return dict(avg=round(sum(vals) / len(vals), 1), delta=round(vals[-1] - vals[0], 1))

    criteria = [
        ("Technical Grammar & Accuracy", "grammar", crit("grammar")),
        ("Pronunciation & Confidence", "pronunciation", crit("pronunciation")),
        ("Fluency & Speaking Rate (WPM)", "fluency", crit("fluency")),
        ("Engineering & Data Vocabulary", "technical_precision", crit("technical_precision")),
    ]
    terms = {t.lower() for s in subs for t in s.found_list}
    last_comment = next((s for s in reversed(subs) if s.teacher_comment), None)
    chart = dict(labels=[f"#{i + 1}" for i in range(len(subs))], scores=scored)
    return render_template("progress.html", student=student, students=students, subs=subs,
                           avg=avg, level=level_from_score(avg) if scored else "-",
                           n_terms=len(terms), criteria=criteria, last_comment=last_comment,
                           chart=chart)




@app.post("/submissions/<int:sub_id>/delete")
@login_required("student")
def delete_submission(sub_id):
    submission = db.get_or_404(Submission, sub_id)

    # Vérifier que la tentative appartient à l'étudiant connecté
    if submission.student_id != g.user.id:
        abort(403)

    audio_filename = submission.audio_filename

    # Supprimer la tentative et ses erreurs grammaticales
    db.session.delete(submission)
    db.session.commit()

    # Supprimer également le fichier audio s'il existe
    if audio_filename:
        audio_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            os.path.basename(audio_filename)
        )

        try:
            if os.path.isfile(audio_path):
                os.remove(audio_path)
        except OSError as e:
            print("Erreur suppression audio :", e)

    return redirect(url_for("progress"))

# ---------------------------------------------------------------- commandes
@app.cli.command("seed")
def seed_command():
    """Remplit la base avec des donnees de demonstration."""
    from seed import run
    run()
    print("Base de demonstration creee.")


if __name__ == "__main__":
    app.run(debug=True)

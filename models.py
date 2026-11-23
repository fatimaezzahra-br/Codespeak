from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def split_list(text):
    return [x.strip() for x in (text or "").split(",") if x.strip()]


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # "teacher" ou "student"
    student_code = db.Column(db.String(30))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        parts = self.full_name.replace("Pr.", "").split()
        return "".join(p[0] for p in parts[:2]).upper()


class Exercise(db.Model):
    __tablename__ = "exercises"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30))
    title = db.Column(db.String(200), nullable=False)
    situation = db.Column(db.String(30), nullable=False)
    level = db.Column(db.String(5), nullable=False)
    duration = db.Column(db.Integer, default=90)
    keywords = db.Column(db.Text, default="")  # mots separes par des virgules
    instructions = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    submissions = db.relationship(
        "Submission", backref="exercise", cascade="all, delete-orphan"
    )

    @property
    def keyword_list(self):
        return split_list(self.keywords)

    @property
    def avg_score(self):
        vals = [s.score_global for s in self.submissions if s.score_global is not None]
        return round(sum(vals) / len(vals), 1) if vals else None


class Submission(db.Model):
    __tablename__ = "submissions"
    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    audio_filename = db.Column(db.String(200))
    duration = db.Column(db.Integer, default=0)
    transcript = db.Column(db.Text, default="")
    wpm = db.Column(db.Integer, default=0)
    fluency = db.Column(db.Float)
    technical_precision = db.Column(db.Float)
    grammar = db.Column(db.Float)
    pronunciation = db.Column(db.Float)
    score_global = db.Column(db.Float)
    vocab_found = db.Column(db.Text, default="")
    vocab_missed = db.Column(db.Text, default="")
    fillers = db.Column(db.Integer, default=0)
    suggestion = db.Column(db.Text, default="")
    teacher_comment = db.Column(db.Text, default="")
    status = db.Column(db.String(15), default="a_evaluer")  # "a_evaluer" ou "evalue"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User")
    issues = db.relationship(
        "GrammarIssue",
        backref="submission",
        cascade="all, delete-orphan",
        order_by="GrammarIssue.id",
    )

    @property
    def found_list(self):
        return split_list(self.vocab_found)

    @property
    def missed_list(self):
        return split_list(self.vocab_missed)


class GrammarIssue(db.Model):
    __tablename__ = "grammar_issues"
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)
    category = db.Column(db.String(100))
    original = db.Column(db.String(300))
    correction = db.Column(db.String(300))
    explanation = db.Column(db.Text)
    priority = db.Column(db.String(20))

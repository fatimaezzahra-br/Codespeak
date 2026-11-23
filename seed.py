"""Donnees de demonstration : python seed.py"""
from datetime import datetime, timedelta

from app import app
from models import Exercise, GrammarIssue, Submission, User, db

SAMPLE = (
    "Good morning team. During yesterday's peak load at 14:00 UTC, the server was crashed "
    "abruptly after experiencing an unprecedented latency spike.\n\n"
    "Upon initial triage, our telemetry indicated that the primary database connection pool "
    "exhausted all available sockets within 42 seconds, severely degrading system throughput. "
    "Unfortunately, we didn't found the root cause immediately because thread logs were truncated.\n\n"
    "After executing a remote thread dump, we identified an unindexed sub-query creating severe "
    "deadlock contention on the user session table. If we would have monitored the wait states "
    "proactively, the cascading crash would have been avoided. As a temporary mitigation, we "
    "enforced circuit breakers for graceful degradation."
)
SAMPLE_ISSUES = [
    ("Voix passive inappropriée", "the server was crashed", "the server crashed",
     "Le verbe « to crash » n'a pas de passif ici : le serveur s'arrête tout seul.", "B1 -> B2"),
    ("Auxiliaire + passé simple", "we didn't found", "we didn't find",
     "Après « didn't », le verbe reste à l'infinitif (find), pas au passé.", "A2 -> B1"),
    ("Third conditional (3e conditionnel)", "If we would have monitored", "If we had monitored",
     "Dans la proposition avec « if », on utilise « had + participe passé ».", "B2 -> C1"),
]
GENERIC = ("Good morning everyone. Today I will present my technical solution. First I describe the "
           "problem, then the architecture, and finally the results and the next steps for the team.")


def user(name, email, pwd, role, code=None):
    u = User(full_name=name, email=email, role=role, student_code=code)
    u.set_password(pwd)
    db.session.add(u)
    return u


def run():
    db.drop_all()
    db.create_all()
    now = datetime.utcnow()
    teacher = user("Pr. M. Nid Hssan", "m.nidhssan@ensiasd.ac.ma", "teacher123", "teacher")
    yas = user("Yassine Benali", "y.benali@ensiasd.ac.ma", "student123", "student", "ENSIASD-2024-041")
    sal = user("Salma Idrissi", "s.idrissi@ensiasd.ac.ma", "student123", "student", "ENSIASD-2024-018")
    oth = user("Othmane El Amrani", "o.elamrani@ensiasd.ac.ma", "student123", "student", "ENSIASD-2024-009")
    ken = user("Kenza Berrada", "k.berrada@ensiasd.ac.ma", "student123", "student", "ENSIASD-2024-033")
    db.session.flush()

    defs = [
        ("MGSI-ENG-001", "Incident Post-Mortem: Microservices Outage", "bug_explanation", "B2", 90, "latency,failover,kubernetes"),
        ("MGSI-ENG-002", "AI Governance & LLM Hallucinations Pitch", "client_presentation", "C1", 120, "ethics,rag-pipeline,grounding"),
        ("MGSI-ENG-003", "Technical Interview: Hash Maps & Collisions", "job_interview", "B1", 60, "complexity,bucket"),
        ("SYS-ENG-402", "Bug Explanation: Database Connection Timeout", "bug_explanation", "B2", 90,
         "database connection pool,latency spike,throughput,thread dump,deadlock contention,graceful degradation"),
        ("MGSI-ENG-005", "Architecture Pitch: Microservices vs Monolith", "client_presentation", "C1", 120, "scalability,latency,deployment"),
        ("MGSI-ENG-006", "Code Review Argument: Refactoring Async Pipeline", "job_interview", "B2", 90, "refactoring,concurrency,throughput"),
    ]
    exs = []
    for i, (code, title, sit, lvl, dur, kw) in enumerate(defs):
        e = Exercise(code=code, title=title, situation=sit, level=lvl, duration=dur, keywords=kw,
                     instructions="Structurez votre discours : 1. Description du problème, 2. Hypothèse technique, 3. Solution et métriques.",
                     created_by=teacher.id, created_at=now - timedelta(days=20 - i * 3))
        db.session.add(e)
        exs.append(e)
    db.session.flush()

    scores = [6.2, 6.8, 7.0, 7.4, 7.6, 7.9, 7.6, 7.9, 8.0, 8.2, 8.4, 8.5]
    for i, sc in enumerate(scores):
        e = exs[i % 6] if i < 11 else exs[3]
        last = i == 11
        words = e.keyword_list
        s = Submission(
            exercise_id=e.id, student_id=yas.id, duration=84 + i, wpm=120 + i,
            transcript=SAMPLE if last else GENERIC + " " + " ".join(words) + ".",
            fluency=min(10, sc + 0.3), technical_precision=min(10, sc + 0.5),
            grammar=max(0, sc - 0.8), pronunciation=sc, score_global=sc,
            vocab_found=",".join(words[:4]) if not last else ",".join(words),
            vocab_missed="" if last else ",".join(words[4:]), fillers=0,
            suggestion="Utilise les collocations « mitigate cascading failures » ou « backpressure handling ».",
            teacher_comment=("Very clear structural explanation. Pay attention to your conditional tenses "
                             "in the mitigation proposal.") if last or i % 3 == 0 else "",
            status="evalue", created_at=now - timedelta(days=(11 - i) * 7),
        )
        if last:
            s.created_at = now - timedelta(hours=2)
            for cat, o, c, ex_, pr in SAMPLE_ISSUES:
                s.issues.append(GrammarIssue(category=cat, original=o, correction=c, explanation=ex_, priority=pr))
        db.session.add(s)

    others = [(sal, exs[4], 9.0, "evalue", 1), (oth, exs[2], 6.5, "a_evaluer", 26), (ken, exs[0], 7.5, "a_evaluer", 30)]
    for st, e, sc, status, hours in others:
        db.session.add(Submission(
            exercise_id=e.id, student_id=st.id, duration=80, wpm=118, transcript=GENERIC,
            fluency=sc, technical_precision=sc, grammar=sc, pronunciation=sc, score_global=sc,
            vocab_found=",".join(e.keyword_list[:2]), vocab_missed=",".join(e.keyword_list[2:]),
            status=status, created_at=now - timedelta(hours=hours)))
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        run()
    print("Base de demonstration creee.")

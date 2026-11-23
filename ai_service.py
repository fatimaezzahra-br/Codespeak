"""Transcription et analyse de l'expression orale.

Ordre de priorite :
1. Transcription : texte envoye par le navigateur (Chrome) -> sinon Whisper (OPENAI_API_KEY).
2. Analyse : Claude (ANTHROPIC_API_KEY) -> sinon regles simples (toujours disponibles).
"""
import json
import re

from config import Config

FILLERS = ["um", "uh", "uhm", "erm", "euh", "you know"]

# ---------- 1. Transcription ----------


def transcribe(path):
    """Transcrit un fichier audio avec Whisper. Retourne "" si indisponible."""
    if not Config.OPENAI_API_KEY:
        return ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        with open(path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1", file=f, language="en"
            )
        return result.text.strip()
    except Exception as e:  # on ne bloque jamais l'application
        print("Erreur transcription :", e)
        return ""


# ---------- 2. Statistiques simples (toujours calculees localement) ----------


def basic_stats(transcript, keywords, duration):
    words = re.findall(r"[A-Za-z'’-]+", transcript)
    if not duration:
        duration = max(1, round(len(words) / 2.3))
    wpm = round(len(words) / (duration / 60))
    low = transcript.lower()
    found = [k for k in keywords if k.lower() in low]
    missed = [k for k in keywords if k.lower() not in low]
    fillers = sum(len(re.findall(r"\b" + re.escape(f) + r"\b", low)) for f in FILLERS)
    return dict(duration=duration, wpm=wpm, found=found, missed=missed, fillers=fillers)


# ---------- 3. Analyse par regles (sans internet) ----------

IRREGULAR = {"found": "find", "went": "go", "saw": "see", "made": "make",
             "took": "take", "knew": "know", "had": "have"}
THIRD_PERSON = {"have": "has", "do": "does", "don't": "doesn't"}

RULES = [
    (r"\b(?:was|were) (crashed|failed|happened|occurred|disappeared)\b",
     lambda m: m.group(1),
     "Voix passive inappropriée",
     "Ces verbes n'ont pas de passif : on dit « it crashed », pas « it was crashed ».",
     "B1 -> B2"),
    (r"\bdidn'?t (found|went|saw|made|took|knew|had)\b",
     lambda m: "didn't " + IRREGULAR[m.group(1).lower()],
     "Auxiliaire + passé simple",
     "Après « didn't », le verbe reste à l'infinitif (didn't find), pas au passé.",
     "A2 -> B1"),
    (r"\bif (we|I|you|they|he|she|it) would have\b",
     lambda m: "if " + m.group(1) + " had",
     "Third conditional (3e conditionnel)",
     "Dans la proposition avec « if », on met « had + participe passé », jamais « would have ».",
     "B2 -> C1"),
    (r"\bI am agree\b",
     lambda m: "I agree",
     "Verbe « agree »",
     "« Agree » est déjà un verbe : on dit « I agree », sans « am ».",
     "A2 -> B1"),
    (r"\bmore (faster|slower|bigger|easier|better)\b",
     lambda m: m.group(1),
     "Comparatif doublé",
     "Ne mets pas « more » devant un comparatif qui finit déjà en -er.",
     "A2 -> B1"),
    (r"\b(he|she|it) (have|do|don't)\b",
     lambda m: m.group(1) + " " + THIRD_PERSON[m.group(2).lower()],
     "Accord sujet-verbe",
     "À la 3e personne du singulier, on dit has / does / doesn't.",
     "A2 -> B1"),
]


def rule_based_analysis(transcript, stats, keywords):
    issues = []
    for pattern, fix, category, explanation, priority in RULES:
        for m in re.finditer(pattern, transcript, re.I):
            issues.append(dict(
                category=category,
                original=m.group(0),
                correction=re.sub(pattern, fix, m.group(0), flags=re.I),
                explanation=explanation,
                priority=priority,
            ))
    coverage = len(stats["found"]) / len(keywords) if keywords else 0.7
    wpm = stats["wpm"]
    fluency = 9.0 if 110 <= wpm <= 170 else 7.5 if 90 <= wpm <= 190 else 6.0
    fluency -= 0.5 * (stats["fillers"] // 2)
    grammar = max(4.0, 10 - 1.2 * len(issues))
    precision = 5 + 5 * coverage
    pronunciation = (fluency + grammar) / 2  # estimation (pas d'analyse des sons)
    if stats["missed"]:
        suggestion = "Essaie d'utiliser aussi : " + ", ".join(stats["missed"][:3]) + "."
    else:
        suggestion = "Très bon vocabulaire. Essaie des collocations plus soutenues."
    return dict(
        fluency=fluency, grammar=grammar, technical_precision=precision,
        pronunciation=pronunciation, issues=issues, suggestion=suggestion,
    )


# ---------- 4. Analyse par Claude ----------

SYSTEM_PROMPT = (
    "You are an examiner of English oral expression for software engineering students "
    "(CEFR levels). Answer with ONE JSON object only, no text around it."
)


def claude_analysis(transcript, exercise, stats):
    import anthropic

    client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    prompt = f"""Exercise: {exercise.title}
Target CEFR level: {exercise.level}
Required technical keywords: {', '.join(exercise.keyword_list)}
Speaking rate: {stats['wpm']} words per minute

Transcript of the student's answer:
\"\"\"{transcript}\"\"\"

Return this JSON:
{{"fluency": 0-10, "grammar": 0-10, "technical_precision": 0-10,
 "pronunciation": 0-10 (estimate from the transcript only),
 "issues": [{{"category": "short French label", "original": "EXACT excerpt copied from the transcript",
   "correction": "corrected version", "explanation": "1-2 simple sentences in French",
   "priority": "e.g. B1 -> B2"}}],
 "suggestion": "one sentence in French to improve the score"}}
Give at most 5 issues. Only real grammar mistakes."""
    resp = client.messages.create(
        model=Config.ANTHROPIC_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    data = json.loads(text)
    clamp = lambda v: max(0.0, min(10.0, float(v)))
    return dict(
        fluency=clamp(data["fluency"]),
        grammar=clamp(data["grammar"]),
        technical_precision=clamp(data["technical_precision"]),
        pronunciation=clamp(data["pronunciation"]),
        issues=[i for i in data.get("issues", []) if i.get("original") in transcript][:5],
        suggestion=data.get("suggestion", ""),
    )


# ---------- 5. Fonction principale ----------


def analyze(transcript, exercise, duration):
    keywords = exercise.keyword_list
    stats = basic_stats(transcript, keywords, duration)
    result = None
    if Config.ANTHROPIC_API_KEY:
        try:
            result = claude_analysis(transcript, exercise, stats)
        except Exception as e:
            print("Erreur Claude, bascule sur les regles :", e)
    if result is None:
        result = rule_based_analysis(transcript, stats, keywords)

    scores = [result[k] for k in ("fluency", "technical_precision", "grammar", "pronunciation")]
    result["score_global"] = round(sum(scores) / 4, 1)
    for k in ("fluency", "technical_precision", "grammar", "pronunciation"):
        result[k] = round(result[k], 1)
    result.update(stats)
    return result

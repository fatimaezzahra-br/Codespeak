# CodeSpeak — Oral Mastery for Engineers

Application web qui aide le professeur d'anglais à faire pratiquer l'expression orale technique
aux étudiants ingénieurs (ENSIASD, MGSI-1).

**Le professeur** crée des exercices (situation, niveau CECRL, vocabulaire obligatoire), écoute les
enregistrements, corrige et suit les notes de la classe.
**L'étudiant** enregistre sa réponse en anglais, reçoit une transcription, ses erreurs de grammaire
expliquées, son vocabulaire technique validé, et suit sa progression.

## Technologies
Flask · SQLAlchemy (SQLite par défaut, MySQL possible) · Tailwind CSS · Chart.js ·
MediaRecorder + SpeechRecognition (navigateur) · API Claude (optionnelle) · Whisper (optionnel)

## Installation
```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Linux/Mac : source venv/bin/activate)
pip install -r requirements.txt
python seed.py                   # crée la base + données de démonstration
python app.py                    # ouvre http://127.0.0.1:5000
```
Utiliser **Chrome ou Edge** (transcription vocale gratuite du navigateur).

## Comptes de démonstration
| Rôle | Email | Mot de passe |
|---|---|---|
| Enseignant | m.nidhssan@ensiasd.ac.ma | teacher123 |
| Étudiant | y.benali@ensiasd.ac.ma | student123 |

## Passer sur MySQL
1. Créer la base : `CREATE DATABASE codespeak CHARACTER SET utf8mb4;`
2. Copier `.env.example` en `.env` et mettre :
   `DATABASE_URL=mysql+pymysql://root:MOT_DE_PASSE@localhost/codespeak`
3. Relancer `python seed.py` puis `python app.py`.

## Correction par IA (optionnel)
Sans clé, l'application utilise des règles de grammaire simples (voix passive, didn't + passé,
third conditional, accord sujet-verbe...). Avec `ANTHROPIC_API_KEY` dans `.env`, la correction est
faite par Claude. Avec `OPENAI_API_KEY`, l'audio est transcrit côté serveur par Whisper.
La note de prononciation est une **estimation** à partir du texte (pas d'analyse des sons).

## Structure
```
app.py              routes Flask (login, dashboard, exercices, feedback, progression)
models.py           tables : users, exercises, submissions, grammar_issues
ai_service.py       transcription + analyse (Claude ou règles)
seed.py             données de démonstration
templates/          pages HTML (Jinja + Tailwind)
static/js/          recorder.js (micro) · dashboard.js (formulaire)
uploads/            enregistrements audio (ignoré par Git)
```

## Idées d'amélioration
Protection CSRF (Flask-WTF), export PDF de la fiche mémo, inscription des étudiants par le professeur.

// Enregistrement audio + transcription (Chrome) + envoi au serveur Flask.
(() => {
  const root = document.getElementById("recorder");
  if (!root) return;

  const btn = document.getElementById("rec-btn");
  const timerEl = document.getElementById("timer");
  const statusEl = document.getElementById("status");
  const manual = document.getElementById("manual");
  const sendText = document.getElementById("send-text");
  const url = root.dataset.submitUrl;
  const maxSeconds = parseInt(root.dataset.max, 10) || 90;

  let recorder, chunks = [], startTime, tick, finalText = "", recording = false;

  const fmt = (s) => String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
  const setStatus = (t) => (statusEl.textContent = t);

  async function send(blob, duration, transcript) {
    setStatus("Analyse en cours... (quelques secondes)");
    btn.disabled = true;
    const fd = new FormData();
    if (blob) fd.append("audio", blob, "answer.webm");
    fd.append("duration", duration);
    fd.append("transcript", transcript);
    try {
      const res = await fetch(url, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur serveur");
      window.location = data.url;
    } catch (e) {
      setStatus("Erreur : " + e.message);
      btn.disabled = false;
    }
  }

  async function start() {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      setStatus("Micro refusé ou introuvable. Utilise l'option « écrire le texte ».");
      return;
    }
    chunks = []; finalText = "";
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const duration = Math.round((Date.now() - startTime) / 1000);
      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      // petit delai avant l'envoi de l'audio au serveur
      setTimeout(() => send(blob, duration, finalText.trim()), 700);
    };

    // Transcription navigateur désactivée dans l'application Desktop.
// La transcription sera effectuée côté serveur.

    recorder.start();
    startTime = Date.now();
    recording = true;
    btn.textContent = "⏹";
    btn.classList.replace("bg-brand", "bg-red-600");
    setStatus("Enregistrement... clique pour terminer.");
    tick = setInterval(() => {
      const s = Math.round((Date.now() - startTime) / 1000);
      timerEl.textContent = fmt(s);
      if (s >= maxSeconds + 15) stop();
    }, 500);
  }

  function stop() {
    if (!recording) return;
    recording = false;
    clearInterval(tick);
    recorder.stop();
    setStatus("Traitement de l'enregistrement...");
  }

  btn.addEventListener("click", () => (recording ? stop() : start()));
  if (sendText)
    sendText.addEventListener("click", () => {
      const text = manual.value.trim();
      if (text.split(/\s+/).length < 5) return setStatus("Écris au moins une phrase complète.");
      send(null, 0, text);
    });
})();

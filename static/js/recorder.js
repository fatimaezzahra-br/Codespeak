document.addEventListener("DOMContentLoaded", () => {
  const box = document.getElementById("recorder");
  if (!box) return;

  const submitUrl = box.dataset.submitUrl;
  const maxDuration = parseInt(box.dataset.max || "60", 10);
  const recBtn = document.getElementById("rec-btn");
  const timerEl = document.getElementById("timer");
  const statusEl = document.getElementById("status");
  const manualEl = document.getElementById("manual");
  const sendTextBtn = document.getElementById("send-text");

  // Zone d'aperçu en direct sous le statut
  const liveBox = document.createElement("div");
  liveBox.className = "mt-4 p-3 rounded-xl bg-lav/40 text-xs text-slate-700 text-left hidden";
  statusEl.insertAdjacentElement("afterend", liveBox);

  let mediaRecorder = null;
  let audioChunks = [];
  // SpeechRecognition disabled: transcription is handled by Faster-Whisper on the server. let recognition = null;
  let isRecording = false;
  let finalTranscript = "";
  let interimTranscript = "";
  let seconds = 0;
  let timerInterval = null;

  function formatTime(s) {
    const m = String(Math.floor(s / 60)).padStart(2, "0");
    const sec = String(s % 60).padStart(2, "0");
    return `${m}:${sec}`;
  }

  

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      finalTranscript = "";
      interimTranscript = "";
      seconds = 0;
      timerEl.textContent = "00:00";
      liveBox.classList.add("hidden");
      liveBox.textContent = "";

      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunks, { type: "audio/webm" });
        const fullText = "";
        await sendSubmission(blob, fullText, seconds);
      };

      mediaRecorder.start();
      isRecording = true;

      

      recBtn.textContent = "⏹";
      recBtn.classList.add("animate-pulse", "bg-rose-600");
      statusEl.textContent = "Enregistrement en cours... Parlez en anglais puis cliquez pour arrêter.";

      timerInterval = setInterval(() => {
        seconds++;
        timerEl.textContent = formatTime(seconds);
        if (seconds >= maxDuration) stopRecording();
      }, 1000);
    } catch (err) {
      statusEl.textContent = "Erreur micro : autorisez l'accès au microphone dans votre navigateur.";
      console.error(err);
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    clearInterval(timerInterval);

    

    recBtn.textContent = "🎙";
    recBtn.classList.remove("animate-pulse", "bg-rose-600");
    statusEl.textContent = "Analyse de votre réponse en cours...";

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
  }

  async function sendSubmission(audioBlob, transcriptText, durationSec) {
    const fd = new FormData();
    if (audioBlob) fd.append("audio", audioBlob, "record.webm");
    fd.append("transcript", transcriptText);
    fd.append("duration", String(durationSec));

    try {
      const res = await fetch(submitUrl, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        statusEl.textContent = "Erreur : " + (data.error || "Échec de l'envoi.");
        // Pré-remplir le champ manuel si du texte a été partiellement capté
        if (transcriptText && manualEl) manualEl.value = transcriptText;
        return;
      }
      window.location.href = data.url;
    } catch (e) {
      statusEl.textContent = "Erreur réseau lors de l'envoi.";
    }
  }

  recBtn.addEventListener("click", () => {
    if (isRecording) stopRecording();
    else startRecording();
  });

  if (sendTextBtn && manualEl) {
    sendTextBtn.addEventListener("click", () => {
      const txt = manualEl.value.trim();
      statusEl.textContent = "Analyse du texte en cours...";
      sendSubmission(null, txt, 0);
    });
  }
});
// Formulaire "Creer un exercice" : curseur de duree + mots-cles (tags).
(() => {
  const slider = document.getElementById("duration");
  const label = document.getElementById("dur-label");
  if (slider) slider.addEventListener("input", () => (label.textContent = slider.value + " secondes"));

  const box = document.getElementById("tags");
  const input = document.getElementById("tag-input");
  const hidden = document.getElementById("keywords");
  if (!box) return;
  const tags = [];

  function render() {
    box.querySelectorAll(".tag").forEach((n) => n.remove());
    tags.forEach((t, i) => {
      const chip = document.createElement("span");
      chip.className = "tag bg-white rounded px-2 py-1 text-xs font-mono flex items-center gap-1";
      chip.textContent = t + " ";
      const x = document.createElement("button");
      x.type = "button"; x.textContent = "×"; x.className = "text-slate-400";
      x.onclick = () => { tags.splice(i, 1); render(); };
      chip.appendChild(x);
      box.insertBefore(chip, input);
    });
    hidden.value = tags.join(",");
  }
  function add(t) {
    t = t.trim().replace(/,/g, "");
    if (t && !tags.includes(t)) { tags.push(t); render(); }
  }
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(input.value); input.value = ""; }
  });
  document.querySelectorAll(".sugg").forEach((b) => b.addEventListener("click", () => add(b.dataset.tag)));
  // ajoute le mot en cours de saisie a l'envoi du formulaire
  box.closest("form").addEventListener("submit", () => { if (input.value.trim()) add(input.value); });
})();

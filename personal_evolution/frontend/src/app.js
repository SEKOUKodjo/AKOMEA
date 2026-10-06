/* Personal Evolution Intelligence : interface téléphone (PWA locale).
   Aucune bibliothèque externe, aucune donnée envoyée hors du réseau local. */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const app = $("#app");

const S = {
  meta: null,
  date: todayISO(),
  pin: safeGet("pei_pin") || "",
  goals: [],
  categories: [],
  morningDraft: null,
  eveningDraft: null,
};

/* Utilitaires */

function safeGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function safeSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } }
function todayISO() { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); }
function shiftISO(iso, days) { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function icon(name, cls = "") { return `<svg class="ic ${cls}" aria-hidden="true"><use href="#i-${name}"/></svg>`; }
function fmtDate(iso, opts = { weekday: "long", day: "numeric", month: "long" }) {
  if (!iso) return "";
  return new Date(iso + "T12:00:00").toLocaleDateString("fr-FR", opts);
}
function fmtMin(m) {
  if (m == null || m === "") return "";
  m = Math.round(m);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${h} h ${String(r).padStart(2, "0")}` : `${h} h`;
}
function pct(x) { return x == null ? "n.d." : `${Math.round(x * 100)} %`; }
function num(v) { if (v === "" || v == null) return null; const n = Number(String(v).replace(",", ".")); return Number.isFinite(n) ? n : null; }
function dimLabel(k) { const d = (S.meta?.dimensions || []).find((x) => x.key === k); return d ? d.label : "Non classé"; }
function dimIcon(k) { const d = (S.meta?.dimensions || []).find((x) => x.key === k); return d ? d.icon : "info"; }
function dimBadge(k) { return `<span class="dim-badge dim-${esc(k || "")}">${icon(dimIcon(k))}</span>`; }

const STATUS = {
  realise: { label: "Réalisé", icon: "check_circle" },
  partiel: { label: "Partiel", icon: "half_circle" },
  non_realise: { label: "Non réalisé", icon: "x_circle" },
  abandonne: { label: "Abandonné", icon: "x" },
  reporte: { label: "Reporté", icon: "skip" },
  prevu: { label: "Prévu", icon: "clock" },
};

function toast(msg, kind = "ok") {
  const t = $("#toast");
  t.className = `toast show ${kind}`;
  t.innerHTML = `${icon(kind === "err" ? "alert" : "check")}<span>${esc(msg)}</span>`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.className = "toast"), 3200);
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (S.pin) headers["X-PEI-PIN"] = S.pin;
  let body = opts.body;
  if (body && !(body instanceof FormData)) { headers["Content-Type"] = "application/json"; body = JSON.stringify(body); }
  const res = await fetch(`/api${path}`, { method: opts.method || (body ? "POST" : "GET"), headers, body });
  if (res.status === 401) { renderLock(); throw new Error("Code PIN requis"); }
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch (e) { /* corps vide */ }
    throw new Error(detail);
  }
  return res.json();
}

async function guard(fn, btn) {
  if (btn) { btn.disabled = true; btn._html = btn.innerHTML; btn.innerHTML = `<span class="spinner"></span>`; }
  try { return await fn(); }
  catch (e) { toast(e.message || "Erreur", "err"); }
  finally { if (btn) { btn.disabled = false; btn.innerHTML = btn._html; } }
}

function loading() { app.innerHTML = `<div class="loading"><span class="spinner"></span></div>`; }
function empty(ic, text) { return `<div class="empty">${icon(ic)}${esc(text)}</div>`; }

/* Composants */

function dimSelect(name, value, extra = "") {
  const opts = (S.meta?.dimensions || []).map((d) => `<option value="${d.key}" ${d.key === value ? "selected" : ""}>${esc(d.label)}</option>`).join("");
  return `<select name="${name}" ${extra}><option value="">Dimension</option>${opts}</select>`;
}
function goalSelect(name, value) {
  const opts = S.goals.filter((g) => g.status === "actif").map((g) => `<option value="${g.id}" ${g.id === value ? "selected" : ""}>${esc(g.title)}</option>`).join("");
  return `<select name="${name}"><option value="">Aucun objectif relié</option>${opts}</select>`;
}
function catDatalist() {
  return `<datalist id="cats">${S.categories.map((c) => `<option value="${esc(c.category)}">`).join("")}</datalist>`;
}
function scale(name, value, legend = ["faible", "élevé"], warm = false) {
  const btns = [1, 2, 3, 4, 5].map((v) => `<button type="button" data-v="${v}" class="${Number(value) === v ? "on" : ""}">${v}</button>`).join("");
  return `<div class="scale ${warm ? "warm" : ""}" data-name="${name}" data-value="${value ?? ""}">${btns}</div>
    <div class="scale-legend"><span>${legend[0]}</span><span>${legend[1]}</span></div>`;
}
function bindScales(root) {
  $$(".scale", root).forEach((sc) => sc.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const same = sc.dataset.value === b.dataset.v;
    sc.dataset.value = same ? "" : b.dataset.v;
    $$("button", sc).forEach((x) => x.classList.toggle("on", !same && x === b));
  }));
}
function scaleVal(root, name) { const sc = $(`.scale[data-name="${name}"]`, root); return sc && sc.dataset.value ? Number(sc.dataset.value) : null; }

function dateBar() {
  return `<div class="datebar">
    <button class="btn ghost icon" data-shift="-1" aria-label="Jour précédent">${icon("chevron_left")}</button>
    <input type="date" id="day-input" value="${S.date}" max="${todayISO()}">
    <button class="btn ghost icon" data-shift="1" aria-label="Jour suivant">${icon("chevron_right")}</button>
  </div>`;
}
function bindDateBar(rerender) {
  $$("[data-shift]").forEach((b) => b.addEventListener("click", () => {
    const next = shiftISO(S.date, Number(b.dataset.shift));
    if (next > todayISO()) return;
    S.date = next; rerender();
  }));
  const inp = $("#day-input");
  if (inp) inp.addEventListener("change", () => { if (inp.value) { S.date = inp.value; rerender(); } });
}

/* Voix : import de fichier audio ou enregistrement direct (HTTPS ou localhost). */
function voiceBlock(id) {
  const canRecord = window.isSecureContext && navigator.mediaDevices && window.MediaRecorder;
  return `<div class="voice" id="${id}">
    ${canRecord ? `<button type="button" class="btn ghost small" data-act="rec">${icon("mic")}Enregistrer</button>` : ""}
    <label class="btn ghost small" style="margin:0">${icon("upload")}Fichier audio
      <input type="file" accept="audio/*" capture hidden data-act="file"></label>
    <span class="status"></span>
  </div>`;
}

function bindVoice(id, moment, onText) {
  const box = $(`#${id}`); if (!box) return;
  const status = $(".status", box);
  const setStatus = (html) => (status.innerHTML = html);

  async function send(blob, name) {
    const fd = new FormData();
    fd.append("file", blob, name);
    fd.append("day", S.date);
    fd.append("moment", moment);
    setStatus(`<span class="spinner" style="border-top-color:var(--green)"></span> Envoi de l'audio`);
    const media = await api("/audio", { body: fd });
    setStatus(`${icon("check", "sm")} Audio conservé. Transcription locale en cours`);
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const m = await api(`/media/${media.id}`);
      if (m.transcription_status === "termine") { setStatus(`${icon("check", "sm")} Transcription terminée`); onText(m.transcription || "", m.id); return; }
      if (m.transcription_status === "indisponible" || m.transcription_status === "erreur") {
        setStatus(`${icon("info", "sm")} Audio conservé. ${esc(m.transcription_error || "Transcription indisponible")} Tu peux saisir le texte.`);
        onText(null, m.id); return;
      }
    }
  }

  const file = $('[data-act="file"]', box);
  file.addEventListener("change", () => { if (file.files[0]) guard(() => send(file.files[0], file.files[0].name)); file.value = ""; });

  const rec = $('[data-act="rec"]', box);
  if (rec) {
    let recorder = null, chunks = [];
    rec.addEventListener("click", async () => {
      if (recorder && recorder.state === "recording") { recorder.stop(); return; }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream); chunks = [];
        recorder.ondataavailable = (e) => chunks.push(e.data);
        recorder.onstop = () => {
          stream.getTracks().forEach((t) => t.stop());
          rec.innerHTML = `${icon("mic")}Enregistrer`;
          const type = recorder.mimeType || "audio/webm";
          guard(() => send(new Blob(chunks, { type }), `enregistrement.${type.includes("mp4") ? "m4a" : "webm"}`));
        };
        recorder.start();
        rec.innerHTML = `<span class="rec-dot"></span>Arrêter`;
        setStatus("Enregistrement en cours");
      } catch (e) { toast("Micro inaccessible : utilise l'import de fichier audio", "err"); }
    });
  }
}

/* Initialisation */

async function loadMeta() {
  if (!S.meta) S.meta = await api("/meta");
  const [goals, cats] = await Promise.all([api("/goals"), api("/categories")]);
  S.goals = goals; S.categories = cats;
}

function renderLock() {
  app.innerHTML = `<div class="lock-screen"><div class="card">
    <h2 style="justify-content:center">${icon("lock")}Accès protégé</h2>
    <p class="muted">Saisis le code PIN défini sur le PC.</p>
    <input type="password" inputmode="numeric" id="pin" placeholder="Code PIN" autocomplete="current-password">
    <div class="btns"><button class="btn block" id="pin-ok">${icon("check")}Déverrouiller</button></div>
  </div></div>`;
  $("#pin-ok").onclick = async () => {
    S.pin = $("#pin").value.trim();
    const r = await fetch("/api/auth/check", { headers: { "X-PEI-PIN": S.pin } });
    if (r.ok) { safeSet("pei_pin", S.pin); S.meta = null; route(); } else toast("Code incorrect", "err");
  };
}

/* Accueil */

async function pageHome() {
  const isToday = S.date === todayISO();
  const [day, summary, insights, review, preds] = await Promise.all([
    api(`/days/${S.date}`), api("/statistics/summary?days=7"), api("/insights?days=90").catch(() => []),
    api("/decisions/to-review").catch(() => []), api(`/predict/day/${S.date}`).catch(() => []),
  ]);
  const predBy = Object.fromEntries(preds.map((p) => [p.intention_id, p]));
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Bonjour" : hour < 18 ? "Bon après midi" : "Bonsoir";
  const d = day.day || {};
  const morningDone = !!d.morning_done_at, eveningDone = !!d.evening_done_at;
  const sum = day.summary;

  const intentions = day.intentions.map((it) => {
    const st = STATUS[it.status] || STATUS.prevu;
    const p = predBy[it.id];
    const prob = it.status === "prevu" && p ? `<span class="chip gray prob" title="Probabilité estimée à partir de ton historique">${icon("cpu", "sm")}${Math.round(p.completion.probability * 100)} %</span>` : "";
    const dur = it.status === "prevu" && p && p.duration && p.duration.predicted !== it.estimated_minutes && p.duration.n >= 3
      ? `<span>${icon("hourglass", "sm")}plutôt ${fmtMin(p.duration.predicted)}</span>` : "";
    return `<div class="item">${dimBadge(it.dimension)}<div class="grow">
        <div class="title">${esc(it.description)}</div>
        <div class="meta"><span class="status-ic ${it.status}">${icon(st.icon, "sm")}${st.label}</span>
          ${it.estimated_minutes ? `<span>${icon("clock", "sm")}${fmtMin(it.estimated_minutes)}</span>` : ""}
          ${it.actual_minutes ? `<span>${icon("check", "sm")}${fmtMin(it.actual_minutes)} réel</span>` : ""}${dur}</div>
      </div>${prob}</div>`;
  }).join("");

  const ins = (insights || []).slice(0, 3).map((i) => `<div class="item insight"><span class="ib">${icon(i.icon || "bulb")}</span>
    <div class="grow"><div class="title">${esc(i.title)}</div><div class="small">${esc(i.message)}</div>
    <div class="caveat">${icon("info", "sm")}${esc(i.caveat || "")}</div></div></div>`).join("");

  app.innerHTML = `
    <div class="card hero">
      <div class="muted small">${esc(fmtDate(S.date, { weekday: "long", day: "numeric", month: "long", year: "numeric" }))}</div>
      <h1 style="color:#fff;margin:4px 0 12px">${icon("star_fill", "hero-star")}${isToday ? greet : "Journée passée"}</h1>
      <div class="kpis">
        <div class="kpi"><div class="v">${sum.n_intentions}</div><div class="l">intentions</div></div>
        <div class="kpi"><div class="v">${sum.completion_rate == null ? "n.d." : pct(sum.completion_rate)}</div><div class="l">réalisation</div></div>
        <div class="kpi"><div class="v">${fmtMin(sum.actual_minutes) || "0"}</div><div class="l">temps suivi</div></div>
      </div>
    </div>
    ${dateBar()}
    <div class="btns" style="margin:0 0 14px">
      <a class="btn ${morningDone ? "ghost" : ""}" href="#/matin">${icon("sun")}${morningDone ? "Intentions saisies" : "Mes intentions"}</a>
      <a class="btn ${eveningDone ? "ghost" : "yellow"}" href="#/soir">${icon("moon")}${eveningDone ? "Bilan fait" : "Bilan du soir"}</a>
    </div>
    <div class="card accent">
      <h2>${icon("target")}Intention, action, résultat</h2>
      ${intentions ? `<div class="list">${intentions}</div>` : empty("sun", "Aucune intention pour cette journée.")}
    </div>
    <div class="card">
      <h2>${icon("chart")}Les 7 derniers jours</h2>
      ${summary.empty ? empty("chart", "Les statistiques apparaîtront après quelques jours de saisie.") : `
      <div class="kpis">
        <div class="kpi"><div class="v">${pct(summary.regularity)}</div><div class="l">régularité</div></div>
        <div class="kpi"><div class="v">${pct(summary.completion_rate)}</div><div class="l">réalisation</div></div>
        <div class="kpi"><div class="v">${summary.total_hours} h</div><div class="l">activités</div></div>
      </div>
      <p class="small muted" style="margin:10px 0 0">Série en cours : ${summary.current_streak} jours. Record : ${summary.longest_streak} jours.</p>`}
    </div>
    ${review.length ? `<div class="card accent-yellow"><h2>${icon("scale")}Décisions à revoir</h2><div class="list">
      ${review.map((r) => `<a class="item" href="#/journal" style="text-decoration:none;color:inherit"><div class="grow"><div class="title">${esc(r.title)}</div>
      <div class="meta"><span>${icon("calendar", "sm")}prise le ${fmtDate(r.date, { day: "numeric", month: "long" })}</span></div></div>${icon("chevron_right")}</a>`).join("")}</div></div>` : ""}
    ${ins ? `<div class="card"><h2>${icon("bulb")}Ce que montrent tes données</h2><div class="list">${ins}</div>
      <div class="btns"><a class="btn ghost small" href="#/bilan">${icon("chart")}Voir le bilan</a></div></div>` : ""}
  `;
  bindDateBar(route);
}

/* Matin */

function intentionEditor(it, idx) {
  return `<div class="edit-item" data-idx="${idx}">
    <button class="btn ghost icon close" data-del="${idx}" aria-label="Retirer">${icon("x")}</button>
    <label>Intention</label>
    <input name="description" value="${esc(it.description)}" style="padding-right:48px">
    <div class="row">
      <div><label>Dimension</label>${dimSelect("dimension", it.dimension)}</div>
      <div><label>Type d'activité</label><input name="category" list="cats" value="${esc(it.category || "")}" placeholder="Python, Sport"></div>
    </div>
    <div class="row">
      <div><label>Durée prévue (min)</label><input name="estimated_minutes" type="number" inputmode="numeric" min="0" value="${it.estimated_minutes ?? it.minutes ?? ""}"></div>
      <div><label>Priorité</label><select name="priority">
        <option value="1" ${it.priority === 1 ? "selected" : ""}>Haute</option>
        <option value="2" ${!it.priority || it.priority === 2 ? "selected" : ""}>Normale</option>
        <option value="3" ${it.priority === 3 ? "selected" : ""}>Basse</option></select></div>
    </div>
    <label>Objectif relié</label>${goalSelect("goal_id", it.goal_id)}
    <div class="hint" data-hint></div>
  </div>`;
}

function readIntentions() {
  return $$("#draft .edit-item").map((el) => ({
    description: $('[name="description"]', el).value.trim(),
    dimension: $('[name="dimension"]', el).value || null,
    category: $('[name="category"]', el).value.trim() || null,
    estimated_minutes: num($('[name="estimated_minutes"]', el).value),
    priority: Number($('[name="priority"]', el).value),
    goal_id: num($('[name="goal_id"]', el).value),
  })).filter((x) => x.description);
}

async function pageMorning() {
  const day = await api(`/days/${S.date}`);
  const d = day.day || {};
  const draft = S.morningDraft && S.morningDraft.date === S.date ? S.morningDraft : { date: S.date, items: [], extraction_id: null, text: "" };
  S.morningDraft = draft;
  const nCount = day.intentions.length + draft.items.length;

  app.innerHTML = `
    <h1>${icon("sun")}Intentions du matin</h1>
    <p class="lead">Ce que tu veux faire aujourd'hui. L'IA propose, tu valides.</p>
    ${dateBar()}
    <div class="card">
      <h2>${icon("sliders")}Comment commences tu la journée ?</h2>
      <div class="row"><div><label>${icon("bed", "sm")} Sommeil (heures)</label><input id="m-sleep" type="number" step="0.25" min="0" max="24" inputmode="decimal" value="${d.sleep_hours ?? ""}"></div>
      <div><label>Qualité du sommeil</label>${scale("sleep_quality", d.sleep_quality, ["mauvaise", "excellente"])}</div></div>
      <label>${icon("zap", "sm")} Énergie</label>${scale("energy", d.energy)}
      <label>${icon("flag", "sm")} Motivation</label>${scale("motivation", d.motivation)}
      <label>${icon("smile", "sm")} Humeur</label>${scale("mood", d.mood, ["basse", "excellente"])}
    </div>
    <div class="card accent">
      <h2>${icon("message")}Dis ou écris tes intentions</h2>
      <textarea id="m-text" placeholder="Aujourd'hui, je veux lire un chapitre de la Bible, faire 30 minutes de sport et travailler deux heures sur mon projet Python.">${esc(draft.text)}</textarea>
      ${voiceBlock("m-voice")}
      <div class="btns"><button class="btn" id="m-parse">${icon("cpu")}Analyser</button>
        <button class="btn ghost" id="m-add">${icon("plus")}Ajouter à la main</button></div>
    </div>
    <div id="draft">${catDatalist()}
      ${draft.items.length ? `<h3>${icon("edit", "sm")} À valider</h3>` : ""}
      ${draft.items.map(intentionEditor).join("")}
    </div>
    ${nCount > 4 ? `<div class="hint warn" style="margin:0 4px 12px">${icon("info", "sm")}Tu prévois ${nCount} intentions. Regarde dans ton bilan si tes journées chargées sont aussi réalisées.</div>` : ""}
    <button class="btn block" id="m-save">${icon("check")}Valider ma matinée</button>
    ${day.intentions.length ? `<div class="card" style="margin-top:14px"><h2>${icon("target")}Déjà enregistrées</h2><div class="list">
      ${day.intentions.map((it) => `<div class="item">${dimBadge(it.dimension)}<div class="grow"><div class="title">${esc(it.description)}</div>
        <div class="meta"><span>${esc(it.category || dimLabel(it.dimension))}</span>${it.estimated_minutes ? `<span>${icon("clock", "sm")}${fmtMin(it.estimated_minutes)}</span>` : ""}</div></div>
        <button class="btn ghost icon" data-rm="${it.id}" aria-label="Supprimer">${icon("trash")}</button></div>`).join("")}</div></div>` : ""}
  `;
  bindDateBar(route);
  bindScales(app);

  const syncDraft = () => { draft.items = readIntentions(); draft.text = $("#m-text").value; };
  const parse = (text, mediaId) => guard(async () => {
    const r = await api("/morning/parse", { body: { text, date: S.date, media_id: mediaId || null } });
    syncDraft();
    draft.items = draft.items.concat(r.items.map((x) => ({ ...x, estimated_minutes: x.minutes })));
    draft.extraction_id = r.extraction_id; draft.text = text;
    if (!r.items.length) toast("Aucune intention reconnue, ajoute les à la main", "err");
    pageMorning();
  }, $("#m-parse"));

  $("#m-parse").onclick = () => { const t = $("#m-text").value.trim(); if (t) parse(t); };
  $("#m-add").onclick = () => { syncDraft(); draft.items.push({ description: "", priority: 2 }); pageMorning(); };
  bindVoice("m-voice", "matin", (text, mediaId) => { if (text) { $("#m-text").value = text; parse(text, mediaId); } });
  $$("[data-del]").forEach((b) => (b.onclick = () => { syncDraft(); draft.items.splice(Number(b.dataset.del), 1); pageMorning(); }));
  $$("[data-rm]").forEach((b) => (b.onclick = () => guard(async () => { await api(`/intentions/${b.dataset.rm}`, { method: "DELETE" }); pageMorning(); })));

  // Calibration : suggestion de durée réaliste à partir de l'historique.
  $$("#draft .edit-item").forEach((el) => {
    const field = $('[name="estimated_minutes"]', el);
    const hint = $("[data-hint]", el);
    const check = async () => {
      const est = num(field.value); if (!est) { hint.innerHTML = ""; return; }
      try {
        const r = await api("/predict/duration", { body: { estimated_minutes: est, category: $('[name="category"]', el).value || null, dimension: $('[name="dimension"]', el).value || null } });
        hint.innerHTML = r.n >= 3 && Math.abs(r.predicted - est) >= 5 ? `${icon("hourglass", "sm")}Historiquement, ce type de tâche prend plutôt ${fmtMin(r.predicted)} (${r.n} observations).` : "";
      } catch (e) { hint.innerHTML = ""; }
    };
    field.addEventListener("change", check); check();
  });

  $("#m-save").onclick = (ev) => guard(async () => {
    syncDraft();
    const metrics = { sleep_hours: num($("#m-sleep").value), sleep_quality: scaleVal(app, "sleep_quality"), energy: scaleVal(app, "energy"),
      motivation: scaleVal(app, "motivation"), mood: scaleVal(app, "mood") };
    Object.keys(metrics).forEach((k) => metrics[k] == null && delete metrics[k]);
    await api("/morning", { body: { date: S.date, intentions: draft.items, metrics, extraction_id: draft.extraction_id, raw_text: draft.extraction_id ? null : (draft.text || null) } });
    S.morningDraft = null;
    toast("Intentions enregistrées. Belle journée.");
    location.hash = "#/";
  }, ev.currentTarget);
}

/* Journée */

async function pageDay() {
  const day = await api(`/days/${S.date}`);
  const kinds = S.meta.reflection_kinds.map((k) => `<option value="${k.key}">${esc(k.label)}</option>`).join("");
  const intentOpts = day.intentions.map((i) => `<option value="${i.id}">${esc(i.description)}</option>`).join("");

  app.innerHTML = `
    <h1>${icon("clock")}Pendant la journée</h1>
    <p class="lead">Note ce que tu fais réellement, au fil de l'eau.</p>
    ${dateBar()}
    <div class="card accent">
      <h2>${icon("check")}Une activité réalisée</h2>
      ${catDatalist()}
      <label>Description</label><input id="a-desc" placeholder="Lecture de 42 minutes sur les arbres de décision">
      ${day.intentions.length ? `<label>Intention correspondante</label><select id="a-int"><option value="">Activité non prévue</option>${intentOpts}</select>` : ""}
      <div class="row"><div><label>Dimension</label>${dimSelect("a-dim", null, 'id="a-dim"')}</div>
        <div><label>Type d'activité</label><input id="a-cat" list="cats"></div></div>
      <div class="row3"><div><label>Durée (min)</label><input id="a-min" type="number" inputmode="numeric" min="0"></div>
        <div><label>Début</label><input id="a-start" type="time"></div><div><label>Fin</label><input id="a-end" type="time"></div></div>
      <label>Résultat obtenu</label><input id="a-res" placeholder="Ce que cela a produit">
      <div class="btns"><button class="btn" id="a-save">${icon("save")}Enregistrer l'activité</button></div>
    </div>
    <div class="card">
      <h2>${icon("message")}Une note, une réflexion</h2>
      <div class="row"><div><label>Type</label><select id="r-kind">${kinds}</select></div><div><label>Dimension</label>${dimSelect("r-dim", null, 'id="r-dim"')}</div></div>
      <label>Contenu</label><textarea id="r-content"></textarea>
      <label>Référence (passage, livre, lien)</label><input id="r-ref" placeholder="Psaume 23">
      <div class="btns"><button class="btn" id="r-save">${icon("save")}Enregistrer la note</button></div>
    </div>
    <div class="card">
      <h2>${icon("image")}Photo, vidéo, audio ou document</h2>
      <p class="small muted" style="margin-top:-4px">Le fichier original est conservé sur le PC. Les audios et vidéos sont transcrits localement.</p>
      <input type="file" id="f-file" accept="image/*,video/*,audio/*,application/pdf,.doc,.docx,.txt">
      <div class="row"><div><label>Dimension</label>${dimSelect("f-dim", null, 'id="f-dim"')}</div><div><label>Légende</label><input id="f-cap"></div></div>
      <div class="btns"><button class="btn" id="f-send">${icon("upload")}Envoyer</button></div>
    </div>
    <div class="card"><h2>${icon("layers")}Aujourd'hui</h2>
      ${day.activities.length + day.reflections.length + day.media.length === 0 ? empty("clock", "Rien de noté pour l'instant.") : ""}
      <div class="list">
      ${day.activities.map((a) => `<div class="item">${dimBadge(a.dimension)}<div class="grow"><div class="title">${esc(a.description)}</div>
        <div class="meta">${a.duration_minutes ? `<span>${icon("clock", "sm")}${fmtMin(a.duration_minutes)}</span>` : ""}${a.category ? `<span>${esc(a.category)}</span>` : ""}
        ${a.planned ? `<span>${icon("link", "sm")}prévu</span>` : `<span>non prévu</span>`}</div>
        ${a.result ? `<div class="small">${icon("arrow_right", "sm")} ${esc(a.result)}</div>` : ""}</div>
        <button class="btn ghost icon" data-rma="${a.id}" aria-label="Supprimer">${icon("trash")}</button></div>`).join("")}
      ${day.reflections.map((r) => `<div class="item">${dimBadge(r.dimension)}<div class="grow"><div class="meta"><span class="chip yellow">${esc((S.meta.reflection_kinds.find((k) => k.key === r.kind) || {}).label || r.kind)}</span>${r.reference ? `<span>${esc(r.reference)}</span>` : ""}</div>
        <div>${esc(r.content)}</div></div><button class="btn ghost icon" data-rmr="${r.id}" aria-label="Supprimer">${icon("trash")}</button></div>`).join("")}
      ${day.media.map((m) => `<div class="item"><span class="dim-badge">${icon(m.type === "audio" ? "mic" : m.type === "video" ? "video" : m.type === "image" ? "image" : "file")}</span>
        <div class="grow"><div class="title"><a href="/api/media/${m.id}/file" target="_blank" rel="noopener">${esc(m.caption || m.original_name)}</a></div>
        <div class="meta"><span>${esc(m.type)}</span>${m.transcription_status ? `<span>transcription : ${esc(m.transcription_status.replace("_", " "))}</span>` : ""}</div>
        ${m.transcription ? `<div class="small">${esc(m.transcription)}</div>` : ""}</div></div>`).join("")}
      </div></div>
  `;
  bindDateBar(route);
  const intSel = $("#a-int");
  if (intSel) intSel.onchange = () => {
    const it = day.intentions.find((i) => String(i.id) === intSel.value);
    if (it) { $("#a-dim").value = it.dimension || ""; $("#a-cat").value = it.category || ""; if (!$("#a-desc").value) $("#a-desc").value = it.description; }
  };
  $("#a-save").onclick = (ev) => guard(async () => {
    const desc = $("#a-desc").value.trim(); if (!desc) throw new Error("Décris l'activité");
    await api("/activities", { body: { date: S.date, description: desc, intention_id: intSel ? num(intSel.value) : null,
      dimension: $("#a-dim").value || null, category: $("#a-cat").value.trim() || null, duration_minutes: num($("#a-min").value),
      start_time: $("#a-start").value || null, end_time: $("#a-end").value || null, result: $("#a-res").value.trim() || null } });
    toast("Activité enregistrée"); pageDay();
  }, ev.currentTarget);
  $("#r-save").onclick = (ev) => guard(async () => {
    const content = $("#r-content").value.trim(); if (!content) throw new Error("La note est vide");
    await api("/reflections", { body: { date: S.date, content, kind: $("#r-kind").value, dimension: $("#r-dim").value || null, reference: $("#r-ref").value.trim() || null } });
    toast("Note enregistrée"); pageDay();
  }, ev.currentTarget);
  $("#f-send").onclick = (ev) => guard(async () => {
    const f = $("#f-file").files[0]; if (!f) throw new Error("Choisis un fichier");
    const fd = new FormData();
    fd.append("file", f, f.name); fd.append("day", S.date); fd.append("moment", "journee");
    if ($("#f-dim").value) fd.append("dimension", $("#f-dim").value);
    if ($("#f-cap").value) fd.append("caption", $("#f-cap").value);
    await api("/media", { body: fd });
    toast("Fichier conservé"); pageDay();
  }, ev.currentTarget);
  $$("[data-rma]").forEach((b) => (b.onclick = () => guard(async () => { await api(`/activities/${b.dataset.rma}`, { method: "DELETE" }); pageDay(); })));
  $$("[data-rmr]").forEach((b) => (b.onclick = () => guard(async () => { await api(`/reflections/${b.dataset.rmr}`, { method: "DELETE" }); pageDay(); })));
}

/* Soir */

function reviewCard(it, rv) {
  const st = rv.status || (it.status !== "prevu" ? it.status : "");
  const segs = ["realise", "partiel", "non_realise", "abandonne", "reporte"].map((k) =>
    `<button type="button" data-v="${k}" class="${st === k ? "on" : ""}">${icon(STATUS[k].icon, "sm")}${STATUS[k].label}</button>`).join("");
  const notDone = ["non_realise", "abandonne", "reporte"].includes(st);
  return `<div class="edit-item ${notDone ? "not-done" : ""}" data-int="${it.id}" data-status="${st}">
    <div style="display:flex;gap:10px;align-items:center">${dimBadge(it.dimension)}<div class="grow"><div class="title">${esc(it.description)}</div>
      <div class="meta">${it.estimated_minutes ? `<span>${icon("clock", "sm")}prévu ${fmtMin(it.estimated_minutes)}</span>` : ""}${it.category ? `<span>${esc(it.category)}</span>` : ""}</div></div></div>
    <div class="seg">${segs}</div>
    <div class="row" data-done ${notDone ? 'style="display:none"' : ""}>
      <div><label>Temps réel (min)</label><input name="actual" type="number" inputmode="numeric" min="0" value="${rv.actual_minutes ?? it.actual_minutes ?? ""}"></div>
      <div><label>Résultat</label><input name="result" value="${esc(rv.result ?? it.result ?? "")}" placeholder="Ce que cela a produit"></div>
    </div>
    <div data-reason ${notDone ? "" : 'style="display:none"'}><label>Pourquoi ?</label><input name="reason" value="${esc(rv.reason ?? it.reason ?? "")}" placeholder="fatigue, imprévu, manque de temps"></div>
    ${rv.from_ai ? `<div class="hint">${icon("cpu", "sm")}Proposé à partir de ton bilan, à vérifier.</div>` : ""}
  </div>`;
}

function extraActivityEditor(a, idx) {
  return `<div class="edit-item" data-extra="${idx}">
    <button class="btn ghost icon close" data-delx="${idx}" aria-label="Retirer">${icon("x")}</button>
    <label>Activité non prévue</label><input name="description" value="${esc(a.description)}" style="padding-right:48px">
    <div class="row"><div><label>Dimension</label>${dimSelect("dimension", a.dimension)}</div><div><label>Type</label><input name="category" list="cats" value="${esc(a.category || "")}"></div></div>
    <div class="row"><div><label>Durée (min)</label><input name="minutes" type="number" min="0" value="${a.minutes ?? ""}"></div><div><label>Résultat</label><input name="result" value="${esc(a.result || "")}"></div></div>
  </div>`;
}

async function pageEvening() {
  const day = await api(`/days/${S.date}`);
  const d = day.day || {};
  const draft = S.eveningDraft && S.eveningDraft.date === S.date ? S.eveningDraft
    : { date: S.date, reviews: {}, extras: [], reflections: [], extraction_id: null, text: "", emotions: [] };
  S.eveningDraft = draft;
  const refl = (kind) => draft.reflections.filter((r) => r.kind === kind).map((r) => r.content).join("\n");

  app.innerHTML = `
    <h1>${icon("moon")}Bilan du soir</h1>
    <p class="lead">Ce que tu voulais faire, ce que tu as fait, ce que cela a produit.</p>
    ${dateBar()}
    <div class="card accent">
      <h2>${icon("message")}Raconte ta journée</h2>
      <textarea id="e-text" placeholder="J'avais prévu deux heures de Python mais j'ai finalement travaillé une heure quinze. J'ai terminé la partie sur les modèles de classification. Je n'ai pas fait de sport parce que j'étais fatigué.">${esc(draft.text)}</textarea>
      ${voiceBlock("e-voice")}
      <div class="btns"><button class="btn" id="e-parse">${icon("cpu")}Analyser et préremplir</button></div>
      ${draft.emotions.length ? `<div class="hint">${icon("smile", "sm")}Émotions repérées : ${draft.emotions.map((e) => esc(e.word)).join(", ")}</div>` : ""}
    </div>
    ${catDatalist()}
    <div class="card">
      <h2>${icon("target")}Mes intentions</h2>
      ${day.intentions.length ? day.intentions.map((it) => reviewCard(it, draft.reviews[it.id] || {})).join("") : empty("sun", "Aucune intention ce matin. Ajoute ci dessous ce que tu as fait.")}
    </div>
    <div class="card">
      <h2>${icon("plus")}Activités non prévues</h2>
      <div id="extras">${draft.extras.map(extraActivityEditor).join("")}</div>
      <button class="btn ghost small" id="e-addx">${icon("plus")}Ajouter une activité</button>
    </div>
    <div class="card">
      <h2>${icon("book")}Ce que je retiens</h2>
      <label>Ce que j'ai appris</label><textarea id="e-learn" style="min-height:70px">${esc(refl("apprentissage"))}</textarea>
      <label>Ce qui a marqué ma journée</label><textarea id="e-high" style="min-height:70px">${esc(d.highlight || refl("evenement"))}</textarea>
      <label>Difficultés rencontrées</label><textarea id="e-diff" style="min-height:70px">${esc(refl("difficulte"))}</textarea>
      <label>Gratitude</label><textarea id="e-grat" style="min-height:70px">${esc(refl("gratitude"))}</textarea>
      <label>Qu'ai je fait aujourd'hui qui contribue à mon évolution professionnelle ?</label>
      <textarea id="e-pro" style="min-height:70px">${esc(d.professional_contribution || "")}</textarea>
    </div>
    <div class="card">
      <h2>${icon("sliders")}Comment s'est passée la journée ?</h2>
      <label>${icon("smile", "sm")} Humeur</label>${scale("mood", d.mood, ["basse", "excellente"])}
      <label>${icon("zap", "sm")} Énergie</label>${scale("energy", d.energy)}
      <label>${icon("alert", "sm")} Stress</label>${scale("stress", d.stress, ["calme", "très stressé"], true)}
      <div class="row3">
        <div><label>${icon("monitor", "sm")} Écran (min)</label><input id="e-screen" type="number" min="0" value="${d.screen_minutes ?? ""}"></div>
        <div><label>${icon("pulse", "sm")} Pas</label><input id="e-steps" type="number" min="0" value="${d.steps ?? ""}"></div>
        <div><label>${icon("droplet", "sm")} Eau (l)</label><input id="e-water" type="number" step="0.1" min="0" value="${d.water_liters ?? ""}"></div>
      </div>
      <label>Commentaire général</label><textarea id="e-comment" style="min-height:60px">${esc(d.general_comment || "")}</textarea>
    </div>
    <button class="btn block yellow" id="e-save">${icon("check")}Enregistrer mon bilan</button>
  `;
  bindDateBar(route);
  bindScales(app);

  $$(".edit-item[data-int]").forEach((card) => {
    $(".seg", card).addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      card.dataset.status = b.dataset.v;
      $$(".seg button", card).forEach((x) => x.classList.toggle("on", x === b));
      const notDone = ["non_realise", "abandonne", "reporte"].includes(b.dataset.v);
      $("[data-done]", card).style.display = notDone ? "none" : "";
      $("[data-reason]", card).style.display = notDone ? "" : "none";
      card.classList.toggle("not-done", notDone);
    });
  });

  const sync = () => {
    draft.text = $("#e-text").value;
    $$(".edit-item[data-int]").forEach((card) => {
      draft.reviews[card.dataset.int] = { ...(draft.reviews[card.dataset.int] || {}), status: card.dataset.status,
        actual_minutes: num($('[name="actual"]', card).value), result: $('[name="result"]', card).value.trim() || null,
        reason: $('[name="reason"]', card).value.trim() || null };
    });
    draft.extras = $$("#extras .edit-item").map((el) => ({ description: $('[name="description"]', el).value.trim(),
      dimension: $('[name="dimension"]', el).value || null, category: $('[name="category"]', el).value.trim() || null,
      minutes: num($('[name="minutes"]', el).value), result: $('[name="result"]', el).value.trim() || null }));
  };

  const parse = (text, mediaId) => guard(async () => {
    sync();
    const r = await api("/evening/parse", { body: { text, date: S.date, media_id: mediaId || null } });
    draft.extraction_id = r.extraction_id; draft.text = text; draft.emotions = r.emotions || [];
    for (const it of r.items) {
      if (it.intention_id) {
        draft.reviews[it.intention_id] = { status: it.status || "realise", actual_minutes: it.minutes, result: it.result,
          reason: it.reason, from_ai: true };
      } else if (it.type === "activite") {
        draft.extras.push({ description: it.description, dimension: it.dimension, category: it.category, minutes: it.minutes, result: it.result });
      }
    }
    draft.reflections = draft.reflections.concat(r.reflections || []);
    toast(`${r.items.length} éléments proposés, à vérifier`);
    pageEvening();
  }, $("#e-parse"));

  $("#e-parse").onclick = () => { const t = $("#e-text").value.trim(); if (t) parse(t); };
  bindVoice("e-voice", "soir", (text, mediaId) => { if (text) { $("#e-text").value = text; parse(text, mediaId); } });
  $("#e-addx").onclick = () => { sync(); draft.extras.push({ description: "" }); pageEvening(); };
  $$("[data-delx]").forEach((b) => (b.onclick = () => { sync(); draft.extras.splice(Number(b.dataset.delx), 1); pageEvening(); }));

  $("#e-save").onclick = (ev) => guard(async () => {
    sync();
    const reviews = Object.entries(draft.reviews).filter(([, v]) => v.status).map(([id, v]) => ({ intention_id: Number(id), status: v.status,
      actual_minutes: ["realise", "partiel"].includes(v.status) ? v.actual_minutes : null, result: v.result, reason: v.reason }));
    const activities = draft.extras.filter((a) => a.description).map((a) => ({ description: a.description, dimension: a.dimension,
      category: a.category, duration_minutes: a.minutes, result: a.result, date: S.date }));
    const reflections = [];
    const addR = (id, kind) => { const v = $(id).value.trim(); if (v) reflections.push({ content: v, kind }); };
    addR("#e-learn", "apprentissage"); addR("#e-diff", "difficulte"); addR("#e-grat", "gratitude");
    const metrics = { mood: scaleVal(app, "mood"), energy: scaleVal(app, "energy"), stress: scaleVal(app, "stress"),
      screen_minutes: num($("#e-screen").value), steps: num($("#e-steps").value), water_liters: num($("#e-water").value),
      highlight: $("#e-high").value.trim() || null, professional_contribution: $("#e-pro").value.trim() || null,
      general_comment: $("#e-comment").value.trim() || null };
    Object.keys(metrics).forEach((k) => metrics[k] == null && delete metrics[k]);
    await api("/evening", { body: { date: S.date, reviews, activities, reflections, metrics, extraction_id: draft.extraction_id,
      raw_text: draft.extraction_id ? null : (draft.text || null) } });
    S.eveningDraft = null;
    toast("Bilan enregistré. Bonne nuit.");
    location.hash = "#/";
  }, ev.currentTarget);
}

/* Plus */

function pageMore() {
  const tiles = [
    ["target", "Objectifs", "Vision et objectifs", "#/objectifs"],
    ["graduation", "Compétences", "Ressenti et preuves", "#/competences"],
    ["scale", "Journal", "Décisions et expériences", "#/journal"],
    ["users", "Relations", "Personnes à entretenir", "#/relations"],
    ["archive", "Mémoire", "Retrouver et interroger", "#/memoire"],
    ["chart", "Bilan", "Tendances et prédictions", "#/bilan"],
    ["calendar", "Historique", "Toutes les journées", "#/historique"],
    ["gauge", "Tableau de bord", "Analyse complète sur le PC", "#/dashboard"],
    ["settings", "Réglages", "Sauvegarde et réseau", "#/reglages"],
  ];
  app.innerHTML = `<h1>${icon("grid")}Plus</h1><div class="tiles">
    ${tiles.map(([ic, t, s, h]) => `<a class="tile" href="${h}">${icon(ic)}<b>${t}</b><small>${s}</small></a>`).join("")}</div>`;
}

/* Objectifs */

async function pageGoals() {
  const progress = await api("/goals/progress");
  const byParent = {};
  progress.forEach((g) => (byParent[g.parent_id ?? "root"] = byParent[g.parent_id ?? "root"] || []).push(g));
  const horizonLabel = Object.fromEntries(S.meta.horizons.map((h) => [h.key, h.label]));
  const node = (g) => `<div class="item" style="margin-bottom:8px">${dimBadge(g.dimension)}<div class="grow">
      <div class="title">${esc(g.title)}</div>
      <div class="meta"><span class="chip ${g.status === "atteint" ? "" : g.status === "abandonne" ? "red" : g.status === "en_pause" ? "gray" : "yellow"}">${esc(horizonLabel[g.horizon] || g.horizon)}</span>
        <span>${g.n_intentions} actions</span><span>${g.hours} h</span>${g.completion_rate != null ? `<span>${pct(g.completion_rate)} réalisé</span>` : ""}
        ${g.days_since_last_action != null ? `<span>${icon("clock", "sm")}il y a ${g.days_since_last_action} j</span>` : ""}</div>
      <div class="btns" style="margin-top:8px">
        ${g.status !== "atteint" ? `<button class="btn ghost small" data-gs="${g.id}" data-v="atteint">${icon("check", "sm")}Atteint</button>` : ""}
        ${g.status === "actif" ? `<button class="btn ghost small" data-gs="${g.id}" data-v="en_pause">${icon("clock", "sm")}Pause</button>` : `<button class="btn ghost small" data-gs="${g.id}" data-v="actif">${icon("play", "sm")}Actif</button>`}
      </div>
      ${(byParent[g.id] || []).length ? `<div class="tree" style="margin-top:10px">${byParent[g.id].map(node).join("")}</div>` : ""}
    </div></div>`;
  const roots = (byParent.root || []).sort((a, b) => Object.keys(horizonLabel).indexOf(a.horizon) - Object.keys(horizonLabel).indexOf(b.horizon));
  app.innerHTML = `
    <h1>${icon("target")}Vision et objectifs</h1>
    <p class="lead">Vision, long terme, année, mois, semaine, puis actions quotidiennes.</p>
    <div class="card">${roots.length ? roots.map(node).join("") : empty("star", "Commence par écrire ta vision.")}</div>
    <div class="card accent"><h2>${icon("plus")}Nouvel objectif</h2>
      <label>Titre</label><input id="g-title">
      <div class="row"><div><label>Horizon</label><select id="g-hor">${S.meta.horizons.map((h) => `<option value="${h.key}" ${h.key === "mensuel" ? "selected" : ""}>${h.label}</option>`).join("")}</select></div>
        <div><label>Dimension</label>${dimSelect("g-dim", null, 'id="g-dim"')}</div></div>
      <label>Objectif parent</label><select id="g-parent"><option value="">Aucun</option>${progress.map((g) => `<option value="${g.id}">${esc(g.title)}</option>`).join("")}</select>
      <div class="row"><div><label>Échéance</label><input id="g-target" type="date"></div><div><label>Indicateur</label><input id="g-metric" placeholder="nombre de projets"></div></div>
      <label>Description</label><textarea id="g-desc" style="min-height:60px"></textarea>
      <div class="btns"><button class="btn" id="g-save">${icon("save")}Créer</button></div>
    </div>`;
  $("#g-save").onclick = (ev) => guard(async () => {
    const title = $("#g-title").value.trim(); if (!title) throw new Error("Titre requis");
    await api("/goals", { body: { title, horizon: $("#g-hor").value, dimension: $("#g-dim").value || null, parent_id: num($("#g-parent").value),
      target_date: $("#g-target").value || null, metric: $("#g-metric").value || null, description: $("#g-desc").value || null } });
    await loadMeta(); toast("Objectif créé"); pageGoals();
  }, ev.currentTarget);
  $$("[data-gs]").forEach((b) => (b.onclick = () => guard(async () => {
    await api(`/goals/${b.dataset.gs}`, { method: "PATCH", body: { status: b.dataset.v } }); pageGoals();
  })));
}

/* Compétences */

async function pageSkills() {
  const skills = await api("/skills");
  app.innerHTML = `
    <h1>${icon("graduation")}Compétences</h1>
    <p class="lead">Ton ressenti, confronté aux preuves observables.</p>
    ${skills.length ? skills.map((s) => `<div class="card">
      <h2>${icon("graduation")}${esc(s.name)}</h2>
      <div class="kpis">
        <div class="kpi"><div class="v">${s.current_rating ?? "n.d."}${s.current_rating != null ? "/5" : ""}</div><div class="l">auto évaluation</div></div>
        <div class="kpi"><div class="v">${s.hours} h</div><div class="l">pratique suivie</div></div>
        <div class="kpi"><div class="v">${s.latest_objective_score ?? "n.d."}</div><div class="l">score objectif</div></div>
      </div>
      <div class="meta small muted" style="margin-top:8px">${s.n_activities} séances, ${s.n_sessions_with_result} avec un résultat.
        ${Object.entries(s.evidence).map(([k, v]) => `${v} ${esc(k)}`).join(", ")}
        ${s.rating_change != null ? ` Évolution du ressenti : ${s.rating_change > 0 ? "+" : ""}${s.rating_change.toFixed(1)}.` : ""}
        ${s.projection ? ` Projection à 3 mois : ${s.projection.projected}/5 (estimation).` : ""}</div>
      <details style="margin-top:8px"><summary>${icon("plus", "sm")}Nouvelle évaluation</summary>
        <div data-skill="${s.id}">
          <label>Auto évaluation</label>${scale(`rate-${s.id}`, null, ["débutant", "expert"])}
          <div class="row"><div><label>Score objectif (0 à 100)</label><input name="score" type="number" min="0" max="100"></div>
            <div><label>Type de preuve</label><select name="etype"><option value="">Aucune</option><option>exercice</option><option>projet</option><option>test</option><option>formation</option><option>production</option></select></div></div>
          <label>Preuve ou commentaire</label><input name="evidence">
          <div class="btns"><button class="btn small" data-addp="${s.id}">${icon("save", "sm")}Enregistrer</button></div>
        </div></details>
    </div>`).join("") : `<div class="card">${empty("graduation", "Aucune compétence suivie.")}</div>`}
    <div class="card accent"><h2>${icon("plus")}Suivre une compétence</h2>
      <div class="row"><div><label>Nom</label><input id="s-name" placeholder="Machine Learning"></div><div><label>Dimension</label>${dimSelect("s-dim", "etudes", 'id="s-dim"')}</div></div>
      <label>Mots clés pour relier les activités</label><input id="s-kw" placeholder="scikit, régression">
      <div class="btns"><button class="btn" id="s-save">${icon("save")}Ajouter</button></div></div>`;
  bindScales(app);
  $("#s-save").onclick = (ev) => guard(async () => {
    const name = $("#s-name").value.trim(); if (!name) throw new Error("Nom requis");
    await api("/skills", { body: { name, dimension: $("#s-dim").value || null, keywords: $("#s-kw").value || null } });
    toast("Compétence ajoutée"); pageSkills();
  }, ev.currentTarget);
  $$("[data-addp]").forEach((b) => (b.onclick = () => guard(async () => {
    const box = $(`[data-skill="${b.dataset.addp}"]`);
    await api(`/skills/${b.dataset.addp}/progress`, { body: { self_rating: scaleVal(box, `rate-${b.dataset.addp}`),
      objective_score: num($('[name="score"]', box).value), evidence_type: $('[name="etype"]', box).value || null,
      evidence: $('[name="evidence"]', box).value || null } });
    toast("Évaluation enregistrée"); pageSkills();
  }, b)));
}

/* Journal : décisions et expériences */

async function pageJournal() {
  const [decisions, experiments] = await Promise.all([api("/decisions"), api("/experiments")]);
  const metricOpts = S.meta.metrics.map((m) => `<option value="${m.key}">${esc(m.label)}</option>`).join("");
  app.innerHTML = `
    <h1>${icon("scale")}Journal</h1>
    <p class="lead">Décision, justification, résultat. Hypothèse, expérience, observation.</p>
    <div class="card"><h2>${icon("compass")}Décisions</h2>
      ${decisions.length ? `<div class="list">${decisions.map((d) => `<div class="item"><div class="grow">
        <div class="title">${esc(d.title)}</div>
        <div class="meta"><span>${icon("calendar", "sm")}${fmtDate(d.date, { day: "numeric", month: "short", year: "numeric" })}</span>${d.confidence ? `<span>confiance ${d.confidence}/5</span>` : ""}
          ${d.outcome_rating ? `<span class="chip">résultat ${d.outcome_rating}/5</span>` : d.review_date ? `<span class="chip yellow">revue le ${fmtDate(d.review_date, { day: "numeric", month: "short" })}</span>` : ""}</div>
        ${d.reasons ? `<div class="small"><b>Raisons :</b> ${esc(d.reasons)}</div>` : ""}${d.choice ? `<div class="small"><b>Choix :</b> ${esc(d.choice)}</div>` : ""}
        ${d.outcome ? `<div class="small"><b>Résultat :</b> ${esc(d.outcome)}</div>` : ""}${d.lessons ? `<div class="small"><b>Leçon :</b> ${esc(d.lessons)}</div>` : ""}
        ${!d.outcome ? `<details><summary>${icon("edit", "sm")}Noter le résultat</summary><div data-dec="${d.id}">
          <label>Résultat observé</label><textarea name="outcome" style="min-height:60px"></textarea>
          <label>Appréciation</label>${scale(`dec-${d.id}`, null, ["mauvaise", "excellente"])}
          <label>Leçon</label><input name="lessons">
          <div class="btns"><button class="btn small" data-decsave="${d.id}">${icon("save", "sm")}Enregistrer</button></div></div></details>` : ""}
      </div></div>`).join("")}</div>` : empty("compass", "Aucune décision enregistrée.")}
      <details style="margin-top:12px"><summary>${icon("plus", "sm")}Nouvelle décision</summary>
        <label>Décision</label><input id="d-title">
        <label>Contexte</label><textarea id="d-ctx" style="min-height:60px"></textarea>
        <label>Raisons</label><textarea id="d-reasons" style="min-height:60px"></textarea>
        <label>Alternatives</label><input id="d-alt">
        <label>Choix effectué</label><input id="d-choice">
        <label>Résultat attendu</label><input id="d-exp">
        <div class="row"><div><label>Revoir le</label><input id="d-review" type="date"></div><div><label>Dimension</label>${dimSelect("d-dim", null, 'id="d-dim"')}</div></div>
        <label>Confiance</label>${scale("d-conf", null, ["faible", "forte"])}
        <div class="btns"><button class="btn" id="d-save">${icon("save")}Enregistrer</button></div>
      </details>
    </div>
    <div class="card"><h2>${icon("flask")}Expériences personnelles</h2>
      ${experiments.length ? `<div class="list">${experiments.map((e) => `<div class="item"><div class="grow">
        <div class="title">${esc(e.title)}</div><div class="small">${esc(e.hypothesis)}</div>
        <div class="meta"><span>${icon("calendar", "sm")}depuis le ${fmtDate(e.start_date, { day: "numeric", month: "short" })}</span><span>${esc((S.meta.metrics.find((m) => m.key === e.metric) || {}).label || e.metric)}</span></div>
        <div class="small" style="margin-top:6px"><span class="chip ${e.analysis.status === "difference" ? "" : "gray"}">${icon("chart", "sm")}${esc(e.analysis.message)}</span></div>
        ${e.analysis.baseline_mean != null ? `<div class="small muted">Avant : ${e.analysis.baseline_mean} sur ${e.analysis.n_baseline} jours. Pendant : ${e.analysis.experiment_mean} sur ${e.analysis.n_experiment} jours.</div>` : ""}
        <div class="caveat small muted" style="display:flex;gap:5px;margin-top:4px">${icon("info", "sm")}${esc(e.analysis.note || "")}</div>
      </div></div>`).join("")}</div>` : empty("flask", "Aucune expérience en cours.")}
      <details style="margin-top:12px"><summary>${icon("plus", "sm")}Nouvelle expérience</summary>
        <label>Titre</label><input id="x-title" placeholder="Quatre objectifs maximum">
        <label>Hypothèse</label><textarea id="x-hyp" style="min-height:60px" placeholder="Je suis plus régulier lorsque je fixe au maximum quatre objectifs par jour."></textarea>
        <label>Ce que je change</label><input id="x-int">
        <div class="row"><div><label>Indicateur observé</label><select id="x-metric">${metricOpts}</select></div><div><label>Début</label><input id="x-start" type="date" value="${todayISO()}"></div></div>
        <div class="btns"><button class="btn" id="x-save">${icon("save")}Lancer</button></div>
      </details>
    </div>`;
  bindScales(app);
  $("#d-save").onclick = (ev) => guard(async () => {
    const title = $("#d-title").value.trim(); if (!title) throw new Error("Titre requis");
    await api("/decisions", { body: { title, context: $("#d-ctx").value || null, reasons: $("#d-reasons").value || null, alternatives: $("#d-alt").value || null,
      choice: $("#d-choice").value || null, expected_outcome: $("#d-exp").value || null, review_date: $("#d-review").value || null,
      dimension: $("#d-dim").value || null, confidence: scaleVal(app, "d-conf") } });
    toast("Décision enregistrée"); pageJournal();
  }, ev.currentTarget);
  $$("[data-decsave]").forEach((b) => (b.onclick = () => guard(async () => {
    const box = $(`[data-dec="${b.dataset.decsave}"]`);
    await api(`/decisions/${b.dataset.decsave}`, { method: "PATCH", body: { title: decisions.find((d) => String(d.id) === b.dataset.decsave).title,
      outcome: $('[name="outcome"]', box).value || null, outcome_rating: scaleVal(box, `dec-${b.dataset.decsave}`), lessons: $('[name="lessons"]', box).value || null } });
    toast("Résultat noté"); pageJournal();
  }, b)));
  $("#x-save").onclick = (ev) => guard(async () => {
    const title = $("#x-title").value.trim(), hyp = $("#x-hyp").value.trim(); if (!title || !hyp) throw new Error("Titre et hypothèse requis");
    await api("/experiments", { body: { title, hypothesis: hyp, intervention: $("#x-int").value || null, metric: $("#x-metric").value, start_date: $("#x-start").value || null } });
    toast("Expérience lancée"); pageJournal();
  }, ev.currentTarget);
}

/* Relations */

async function pagePeople() {
  const people = await api("/people");
  app.innerHTML = `
    <h1>${icon("users")}Relations</h1>
    <p class="lead">Les personnes qui comptent, sans les réduire à un score.</p>
    <div class="card">${people.length ? `<div class="list">${people.map((p) => `<div class="item"><span class="dim-badge dim-relationnel">${icon("user")}</span><div class="grow">
      <div class="title">${esc(p.name)}</div><div class="meta">${p.relation ? `<span>${esc(p.relation)}</span>` : ""}<span>${p.n_interactions} échanges</span>
      ${p.days_since != null ? `<span class="${p.contact_every_days && p.days_since > p.contact_every_days ? "chip red" : ""}">dernier il y a ${p.days_since} j</span>` : ""}</div>
      <div class="btns" style="margin-top:6px">${["appel", "visite", "message", "rencontre"].map((k) => `<button class="btn ghost small" data-pi="${p.id}" data-k="${k}">${k}</button>`).join("")}</div>
      </div></div>`).join("")}</div>` : empty("users", "Aucune personne enregistrée.")}</div>
    <div class="card accent"><h2>${icon("plus")}Ajouter une personne</h2>
      <div class="row"><div><label>Nom</label><input id="p-name"></div><div><label>Relation</label><select id="p-rel"><option>famille</option><option>ami</option><option>collègue</option><option>mentor</option><option>communauté</option></select></div></div>
      <label>Garder contact tous les (jours)</label><input id="p-every" type="number" min="1" placeholder="7">
      <div class="btns"><button class="btn" id="p-save">${icon("save")}Ajouter</button></div></div>`;
  $("#p-save").onclick = (ev) => guard(async () => {
    const name = $("#p-name").value.trim(); if (!name) throw new Error("Nom requis");
    await api("/people", { body: { name, relation: $("#p-rel").value, contact_every_days: num($("#p-every").value) } });
    pagePeople();
  }, ev.currentTarget);
  $$("[data-pi]").forEach((b) => (b.onclick = () => guard(async () => {
    const note = prompt("Une note sur cet échange ? (facultatif)") || null;
    await api("/interactions", { body: { person_id: Number(b.dataset.pi), kind: b.dataset.k, date: S.date, note } });
    toast("Échange noté"); pagePeople();
  })));
}

/* Mémoire */

async function pageMemory() {
  const suggestions = ["Qu'est ce qui m'a marqué le mois dernier ?", "Quels projets ai je terminés cette année ?",
    "Quels sujets ai je le plus étudiés ?", "Quelles difficultés reviennent régulièrement ?", "Comment ai je évolué ce mois ci ?"];
  app.innerHTML = `
    <h1>${icon("archive")}Mémoire personnelle</h1>
    <p class="lead">Pose une question ou cherche un mot. Chaque réponse renvoie à sa source.</p>
    <div class="card accent"><div style="display:flex;gap:8px"><input id="q" placeholder="Que cherches tu ?" enterkeyhint="search">
      <button class="btn icon" id="q-go" aria-label="Chercher">${icon("search")}</button></div>
      <div class="seg" style="margin-top:10px">${suggestions.map((s) => `<button type="button" data-q="${esc(s)}">${esc(s)}</button>`).join("")}</div></div>
    <div id="answer"></div>`;
  const run = (q) => guard(async () => {
    $("#q").value = q;
    $("#answer").innerHTML = `<div class="loading"><span class="spinner"></span></div>`;
    const r = await api(`/memory/ask?q=${encodeURIComponent(q)}`);
    $("#answer").innerHTML = `<div class="card"><h2>${icon("bulb")}${esc(r.answer)}</h2>
      <div class="small muted" style="margin-bottom:8px">Période : ${esc(r.period)}</div>
      ${r.items.length ? `<div class="list">${r.items.map((it) => `<div class="item"><div class="grow">
        <div class="meta"><span class="chip">${esc(it.kind_label)}</span>${it.date ? `<a href="#/jour/${it.date}">${icon("calendar", "sm")}${fmtDate(it.date, { day: "numeric", month: "short", year: "numeric" })}</a>` : ""}</div>
        <div>${esc(it.text).replace(/\[/g, "<mark>").replace(/\]/g, "</mark>")}</div></div></div>`).join("")}</div>` : ""}</div>`;
  });
  $("#q-go").onclick = () => { const q = $("#q").value.trim(); if (q) run(q); };
  $("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#q-go").click(); });
  $$("[data-q]").forEach((b) => (b.onclick = () => run(b.dataset.q)));
  $("#q").focus();
}

/* Bilan */

async function pageReview() {
  const [s30, cal, trends, insights, ab] = await Promise.all([api("/statistics/summary?days=30"), api("/statistics/calibration"),
    api("/statistics/trends"), api("/insights"), api("/statistics/abandons")]);
  const maxMin = Math.max(1, ...(s30.dimensions || []).map((d) => d.minutes));
  app.innerHTML = `
    <h1>${icon("chart")}Bilan</h1>
    <p class="lead">Les 30 derniers jours, tes tendances et des estimations prudentes.</p>
    ${s30.empty ? `<div class="card">${empty("chart", "Pas encore assez de données.")}</div>` : `
    <div class="card hero"><div class="kpis">
      <div class="kpi"><div class="v">${pct(s30.regularity)}</div><div class="l">régularité</div></div>
      <div class="kpi"><div class="v">${pct(s30.completion_rate)}</div><div class="l">réalisation</div></div>
      <div class="kpi"><div class="v">${s30.total_hours} h</div><div class="l">activités suivies</div></div>
      <div class="kpi"><div class="v">${s30.avg_mood ?? "n.d."}</div><div class="l">humeur moyenne</div></div>
      <div class="kpi"><div class="v">${s30.avg_sleep ?? "n.d."}</div><div class="l">sommeil moyen</div></div>
      <div class="kpi"><div class="v">${s30.longest_streak}</div><div class="l">plus longue série</div></div>
    </div></div>
    <div class="card"><h2>${icon("layers")}Temps par dimension</h2>
      ${s30.dimensions.map((d) => `<div class="bar-row"><span class="dim-badge dim-${d.dimension}" style="width:34px;height:34px">${icon(d.icon, "sm")}</span>
        <div><div class="small">${esc(d.label)}${d.completion_rate != null ? ` <span class="muted">(${pct(d.completion_rate)} réalisé)</span>` : ""}</div><div class="bar"><i style="width:${(d.minutes / maxMin) * 100}%"></i></div></div>
        <span class="small" style="text-align:right">${d.hours} h</span></div>`).join("")}
    </div>`}
    <div class="card"><h2>${icon("bulb")}Recommandations</h2>
      ${insights.length ? `<div class="list">${insights.map((i) => `<div class="item insight"><span class="ib">${icon(i.icon || "bulb")}</span><div class="grow">
        <div class="title">${esc(i.title)}</div><div class="small">${esc(i.message)}</div><div class="caveat">${icon("info", "sm")}${esc(i.caveat || "")}</div></div></div>`).join("")}</div>`
        : empty("bulb", "Les recommandations apparaîtront avec l'historique.")}
    </div>
    <div class="card"><h2>${icon("hourglass")}Calibration du temps</h2>
      ${cal.overall ? `<p class="small">${esc(cal.overall.message)} Écart moyen ${cal.overall.mean_error > 0 ? "+" : ""}${cal.overall.mean_error} min sur ${cal.n} tâches.</p>
      <div class="list">${cal.categories.slice(0, 8).map((c) => `<div class="item"><div class="grow"><div class="title">${esc(c.category)}</div>
        <div class="meta"><span>prévu ${c.mean_estimated} min</span><span>réel ${c.mean_actual} min</span><span class="chip ${c.bias === "sous estimation" ? "red" : c.bias === "surestimation" ? "yellow" : ""}">${esc(c.bias)}</span><span>${c.n} obs.</span></div></div></div>`).join("")}</div>`
        : empty("hourglass", "Indique durées prévues et réelles pour calibrer tes estimations.")}
    </div>
    ${trends.length ? `<div class="card"><h2>${icon("trend_up")}Tendances</h2><div class="list">${trends.map((t) => `<div class="item">
      <span class="dim-badge ${t.direction === "baisse" ? "dim-physique" : ""}">${icon(t.direction === "hausse" ? "trend_up" : "trend_down")}</span><div class="grow small">${esc(t.message)}</div></div>`).join("")}</div></div>` : ""}
    ${ab.categories.length ? `<div class="card"><h2>${icon("alert")}Objectifs souvent abandonnés</h2><div class="list">
      ${ab.categories.slice(0, 5).map((c) => `<div class="item"><div class="grow"><div class="title">${esc(c.category)}</div><div class="bar red" style="margin-top:6px"><i style="width:${c.abandon_rate * 100}%"></i></div>
        <div class="meta"><span>${c.abandoned} sur ${c.n}</span></div></div></div>`).join("")}</div>
      ${ab.reasons.length ? `<p class="small muted">Raisons citées : ${ab.reasons.slice(0, 5).map((r) => `${esc(r.reason)} (${r.count})`).join(", ")}.</p>` : ""}</div>` : ""}
    <div class="card accent-yellow"><h2>${icon("route")}Et si je maintenais ce rythme ?</h2>
      ${catDatalist()}
      <div class="row"><div><label>Activité</label><input id="sim-cat" list="cats" placeholder="Python"></div><div><label>Minutes par jour</label><input id="sim-min" type="number" value="90"></div></div>
      <div class="row"><div><label>Pendant (jours)</label><input id="sim-days" type="number" value="90"></div><div><label>Jours par semaine</label><input id="sim-week" type="number" min="1" max="7" value="6"></div></div>
      <div class="btns"><button class="btn yellow" id="sim-go">${icon("play")}Simuler</button></div>
      <div id="sim-out"></div>
    </div>
    <a class="btn block ghost" href="#/dashboard">${icon("gauge")}Ouvrir le tableau de bord complet</a>`;
  $("#sim-go").onclick = (ev) => guard(async () => {
    const cat = $("#sim-cat").value.trim() || null;
    const known = S.categories.find((c) => c.category === cat);
    const r = await api("/simulate", { body: { category: cat, dimension: known ? known.dimension : null, minutes_per_day: num($("#sim-min").value) || 60,
      days: num($("#sim-days").value) || 90, days_per_week: num($("#sim-week").value) || 7 } });
    const maxH = Math.max(1, ...r.histogram);
    $("#sim-out").innerHTML = `<div class="sep"></div><p>${esc(r.message)}</p>
      <div class="kpis"><div class="kpi"><div class="v">${r.hours_p10} h</div><div class="l">scénario prudent</div></div>
      <div class="kpi"><div class="v">${r.hours_median} h</div><div class="l">scénario médian</div></div>
      <div class="kpi"><div class="v">${r.hours_p90} h</div><div class="l">scénario favorable</div></div></div>
      <div class="hist">${r.histogram.map((h) => `<i style="height:${(h / maxH) * 100}%"></i>`).join("")}</div>
      <p class="small muted">Régularité passée ${pct(r.historical_adherence)} sur ${r.n_history} intentions. Déjà ${r.current_hours} h enregistrées. ${esc(r.disclaimer)}</p>`;
  }, ev.currentTarget);
}

/* Historique et détail d'un jour */

async function pageHistory() {
  const days = await api("/days?limit=120");
  app.innerHTML = `<h1>${icon("calendar")}Historique</h1>
    <div class="card">${days.length ? `<div class="list">${days.map((d) => `<a class="item" href="#/jour/${d.date}" style="text-decoration:none;color:inherit">
      <span class="dim-badge">${icon(d.evening_done ? "check_circle" : d.morning_done ? "sun" : "clock")}</span><div class="grow">
      <div class="title">${esc(fmtDate(d.date, { weekday: "long", day: "numeric", month: "long", year: "numeric" }))}</div>
      <div class="meta"><span>${d.summary.n_intentions} intentions</span><span>${pct(d.summary.completion_rate)}</span><span>${fmtMin(d.summary.actual_minutes) || "0 min"}</span>${d.mood ? `<span>${icon("smile", "sm")}${d.mood}/5</span>` : ""}</div>
      ${d.highlight ? `<div class="small">${esc(d.highlight)}</div>` : ""}</div>${icon("chevron_right")}</a>`).join("")}</div>` : empty("calendar", "Aucune journée enregistrée.")}</div>`;
}

async function pageDayDetail(iso) {
  const day = await api(`/days/${iso}`);
  const sources = [...new Set(day.intentions.map((i) => i.source_id).concat(day.activities.map((a) => a.source_id)).filter(Boolean))];
  const srcData = await Promise.all(sources.map((id) => api(`/sources/${id}`).catch(() => null)));
  app.innerHTML = `<h1>${icon("calendar")}${esc(fmtDate(iso, { weekday: "long", day: "numeric", month: "long", year: "numeric" }))}</h1>
    <div class="btns" style="margin:0 0 14px"><button class="btn ghost" id="dd-edit">${icon("edit")}Modifier cette journée</button></div>
    <div class="card"><h2>${icon("route")}Intention, action, résultat</h2>${day.intentions.length ? `<div class="list">${day.intentions.map((it) => `<div class="item">${dimBadge(it.dimension)}<div class="grow">
      <div class="title">${esc(it.description)}</div><div class="meta"><span class="status-ic ${it.status}">${icon((STATUS[it.status] || STATUS.prevu).icon, "sm")}${(STATUS[it.status] || STATUS.prevu).label}</span>
      ${it.estimated_minutes ? `<span>prévu ${fmtMin(it.estimated_minutes)}</span>` : ""}${it.actual_minutes ? `<span>réel ${fmtMin(it.actual_minutes)}</span>` : ""}</div>
      ${it.result ? `<div class="small">${icon("arrow_right", "sm")} ${esc(it.result)}</div>` : ""}${it.reason ? `<div class="small muted">Raison : ${esc(it.reason)}</div>` : ""}</div></div>`).join("")}</div>` : empty("target", "Aucune intention.")}</div>
    ${day.reflections.length ? `<div class="card"><h2>${icon("message")}Réflexions</h2><div class="list">${day.reflections.map((r) => `<div class="item"><div class="grow"><span class="chip yellow">${esc((S.meta.reflection_kinds.find((k) => k.key === r.kind) || {}).label || r.kind)}</span> ${esc(r.content)}</div></div>`).join("")}</div></div>` : ""}
    ${srcData.filter(Boolean).length ? `<div class="card"><h2>${icon("shield")}Sources originales</h2><p class="small muted">Données brutes conservées telles quelles, et ce que l'IA en avait extrait.</p>
      ${srcData.filter(Boolean).map((s) => `<div class="item" style="margin-bottom:8px"><div class="grow"><div class="meta"><span class="chip gray">${esc(s.kind)}</span><span>${esc(s.moment || "")}</span>
      ${s.extractions.map((e) => `<span class="chip ${e.status === "valide" ? "" : e.status === "corrige" ? "yellow" : "gray"}">${esc(e.engine)} : ${esc(e.status)}</span>`).join("")}</div>
      ${s.raw_text ? `<div class="small">${esc(s.raw_text)}</div>` : ""}${s.media_id ? `<a class="small" href="/api/media/${s.media_id}/file" target="_blank">${icon("play", "sm")}Écouter l'original</a>` : ""}</div></div>`).join("")}</div>` : ""}`;
  $("#dd-edit").onclick = () => { S.date = iso; location.hash = "#/soir"; };
}

/* Tableau de bord et réglages */

async function pageDashboard() {
  const info = await api("/system/info");
  const url = `${location.protocol}//${location.hostname}:${info.dashboard_port}`;
  app.innerHTML = `<h1>${icon("gauge")}Tableau de bord</h1>
    <div class="card"><p>Le tableau de bord analytique (Shiny for Python) tourne sur le PC.</p>
    <a class="btn block" href="${url}" target="_blank" rel="noopener">${icon("chart")}Ouvrir ${esc(url)}</a>
    <p class="small muted">S'il ne s'ouvre pas, lance sur le PC : python run.py dashboard --host 0.0.0.0</p></div>`;
}

async function pageSettings() {
  const [info, backups] = await Promise.all([api("/system/info"), api("/system/backups")]);
  app.innerHTML = `<h1>${icon("settings")}Réglages</h1>
    <div class="card"><h2>${icon("wifi")}Réseau local</h2>
      ${info.local_ips.map((ip) => `<div class="item"><div class="grow"><b>http://${esc(ip)}:${location.port || 8000}</b><div class="small muted">Adresse à ouvrir sur le téléphone</div></div></div>`).join("") || "<p class='muted'>Adresse locale inconnue.</p>"}
      <p class="small muted">Pour l'installer : menu du navigateur, puis Ajouter à l'écran d'accueil.</p></div>
    <div class="card"><h2>${icon("cpu")}Intelligence locale</h2>
      <p>Transcription : <b>${info.transcription_engine ? esc(info.transcription_engine) : "non installée"}</b></p>
      ${info.transcription_engine ? "" : `<p class="small muted">Sur le PC : pip install faster-whisper. Les audios restent conservés en attendant.</p>`}
      <p class="small muted">Extraction de texte : moteur à règles en français, sans réseau.</p></div>
    <div class="card"><h2>${icon("archive")}Données</h2><div class="kpis">
      ${Object.entries(info.counts).map(([k, v]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${esc(k)}</div></div>`).join("")}</div>
      <p class="small muted">Base : ${esc(info.database)} (${info.database_mb} Mo)</p></div>
    <div class="card accent"><h2>${icon("shield")}Sauvegarde</h2>
      <div class="btns"><button class="btn" id="bk-go">${icon("download")}Créer une sauvegarde</button></div>
      <div class="list" style="margin-top:10px">${backups.slice(0, 8).map((b) => `<a class="item" href="/api/system/backups/${encodeURIComponent(b.name)}" style="color:inherit;text-decoration:none">${icon("archive")}<div class="grow"><div class="title small">${esc(b.name)}</div><div class="meta"><span>${b.size_mb} Mo</span></div></div>${icon("download")}</a>`).join("")}</div>
      <p class="small muted">Copie ensuite le fichier sur un disque externe ou une clé USB.</p></div>
    <div class="card"><h2>${icon("lock")}Code PIN</h2>
      <p class="small muted">${info.pin_enabled ? "Un code PIN protège l'accès." : "Aucun code PIN. Pour en définir un, lance le serveur avec la variable PEI_PIN."}</p>
      ${info.pin_enabled ? `<button class="btn ghost" id="pin-out">${icon("lock")}Oublier le code sur ce téléphone</button>` : ""}</div>`;
  $("#bk-go").onclick = (ev) => guard(async () => { const r = await api("/system/backup", { method: "POST" }); toast(`Sauvegarde ${r.file} créée`); pageSettings(); }, ev.currentTarget);
  const out = $("#pin-out"); if (out) out.onclick = () => { safeSet("pei_pin", ""); S.pin = ""; renderLock(); };
}

/* Routeur */

const ROUTES = {
  "": ["accueil", pageHome], matin: ["matin", pageMorning], journee: ["journee", pageDay], soir: ["soir", pageEvening],
  plus: ["plus", pageMore], objectifs: ["plus", pageGoals], competences: ["plus", pageSkills], journal: ["plus", pageJournal],
  relations: ["plus", pagePeople], memoire: ["plus", pageMemory], bilan: ["plus", pageReview], historique: ["plus", pageHistory],
  dashboard: ["plus", pageDashboard], reglages: ["plus", pageSettings],
};

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/");
  const [key, arg] = parts;
  let tab, fn;
  if (key === "jour" && arg) { tab = "plus"; fn = () => pageDayDetail(arg); }
  else [tab, fn] = ROUTES[key] || ROUTES[""];
  $$("nav.bottom a").forEach((a) => a.classList.toggle("on", a.dataset.r === tab));
  $("#top-sub").textContent = S.date === todayISO() ? "Observer, comprendre, progresser" : `Saisie du ${fmtDate(S.date, { day: "numeric", month: "long" })}`;
  loading();
  window.scrollTo(0, 0);
  try { await loadMeta(); await fn(); }
  catch (e) { if (e.message !== "Code PIN requis") app.innerHTML = `<div class="card accent-red">${empty("alert", e.message)}</div>`; }
}

$("#btn-search").onclick = () => (location.hash = "#/memoire");
window.addEventListener("hashchange", route);
if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("/service-worker.js").catch(() => {});
route();

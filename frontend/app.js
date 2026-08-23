"use strict";

const API = "http://127.0.0.1:5000/api";

let appState = {
  coins: 256,
  level: 7,
  name: "Prakhar",
  title: "Pippo's Dost",
  mood: {
    mood: "HAPPY",
    emotions: {
      happy: 80,
      curious: 85,
      sad: 15,
      sleepy: 20,
      hungry: 35,
      excited: 70
    },
    personality: {
      brave: 75,
      friendly: 90,
      funny: 80,
      smart: 78,
      lazy: 20,
      curious: 85
    },
    trait: "ADVENTUROUS"
  }
};

const moodEmojis = {
  HAPPY: "😊",
  CURIOUS: "🤔",
  EXCITED: "🤩",
  HUNGRY: "😋",
  SLEEPY: "😴",
  SAD: "😢",
  DEFAULT: "🤖"
};

const greetings = [
  "Namaste Dost! ✋<br><span class='greeting-sub'>I am Pippo. What shall we do today?</span>",
  "Kem cho, dost! 🌟<br><span class='greeting-sub'>Ready for some fun adventures?</span>",
  "Arrey wah! 🎉<br><span class='greeting-sub'>Pippo is super excited to meet you!</span>",
  "Bolo bolo dost! 🤖<br><span class='greeting-sub'>What shall we explore today?</span>"
];

const $ = (id) => document.getElementById(id);
const on = (id, ev, fn) => $(id) && $(id).addEventListener(ev, fn);

document.addEventListener("DOMContentLoaded", () => {
  initParticles();
  renderEmotionsRadar();
  renderPersonalityRadar();
  updateMoodDisplay();
  rotateGreeting();
  wireModals();
  wireRemoteControl();
  wireVoice();
  wireCamera();
  wireCoins();
  wireSettings();
  wireCharacterClick();
  startMoodPolling();
});

function initParticles() {
  const container = $("particles");
  if (!container) return;
  const colors = ["#f6c343", "#ff8a00", "#00f0c0", "#ff4466", "#ffd752"];
  for (let i = 0; i < 22; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    const size = 3 + Math.random() * 5;
    const color = colors[Math.floor(Math.random() * colors.length)];
    p.style.cssText = `
      left: ${Math.random() * 100}%;
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      opacity: ${0.3 + Math.random() * 0.5};
      animation-duration: ${7 + Math.random() * 10}s;
      animation-delay: ${Math.random() * 7}s;
      box-shadow: 0 0 ${size * 2}px ${color};
    `;
    container.appendChild(p);
  }
}

function drawRadar(canvasId, data, colorFill, colorStroke) {
  const canvas = $(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  const cx = W / 2;
  const cy = H / 2;
  const radius = Math.min(W, H) * 0.36;

  const keys = Object.keys(data);
  const values = Object.values(data);
  const n = keys.length;
  const TWO_PI = Math.PI * 2;
  const offset = -Math.PI / 2;

  ctx.clearRect(0, 0, W, H);

  for (let r = 1; r <= 4; r++) {
    const gr = (radius / 4) * r;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const angle = offset + (TWO_PI / n) * i;
      const x = cx + gr * Math.cos(angle);
      const y = cy + gr * Math.sin(angle);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = "rgba(246, 195, 67, 0.25)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  for (let i = 0; i < n; i++) {
    const angle = offset + (TWO_PI / n) * i;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle));
    ctx.strokeStyle = "rgba(246, 195, 67, 0.35)";
    ctx.lineWidth = 1;
    ctx.stroke();

    const labelR = radius + 15;
    const lx = cx + labelR * Math.cos(angle);
    const ly = cy + labelR * Math.sin(angle);
    ctx.fillStyle = "rgba(255, 235, 170, 0.9)";
    ctx.font = "bold 9px 'Baloo 2', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(keys[i].toUpperCase(), lx, ly);
  }

  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const angle = offset + (TWO_PI / n) * i;
    const r = (values[i] / 100) * radius;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();

  ctx.fillStyle = colorFill;
  ctx.fill();
  ctx.strokeStyle = colorStroke;
  ctx.lineWidth = 2.2;
  ctx.stroke();

  for (let i = 0; i < n; i++) {
    const angle = offset + (TWO_PI / n) * i;
    const r = (values[i] / 100) * radius;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, TWO_PI);
    ctx.fillStyle = colorStroke;
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

function renderEmotionsRadar() {
  drawRadar(
    "emotions-radar",
    appState.mood.emotions,
    "rgba(255, 138, 0, 0.38)",
    "#ff9d26"
  );
}

function renderPersonalityRadar() {
  drawRadar(
    "personality-radar",
    appState.mood.personality,
    "rgba(0, 240, 192, 0.32)",
    "#00f0c0"
  );
}

function updateMoodDisplay() {
  const mood = appState.mood.mood;
  const emoji = moodEmojis[mood] || moodEmojis.DEFAULT;
  if ($("mood-emoji")) $("mood-emoji").textContent = emoji;
  if ($("mood-value")) $("mood-value").textContent = mood;
  if ($("trait-value")) $("trait-value").textContent = appState.mood.trait;
}

let greetingIdx = 0;
function rotateGreeting() {
  const el = $("greeting-text");
  if (!el) return;
  setInterval(() => {
    greetingIdx = (greetingIdx + 1) % greetings.length;
    el.style.opacity = "0";
    setTimeout(() => {
      el.innerHTML = greetings[greetingIdx];
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "1";
    }, 400);
  }, 9000);
}

function startMoodPolling() {
  fetchMood();
  setInterval(fetchMood, 5000);
}

async function fetchMood() {
  try {
    const res = await fetch(`${API}/mood`);
    if (!res.ok) return;
    const data = await res.json();
    appState.mood = data;
    updateMoodDisplay();
    renderEmotionsRadar();
    renderPersonalityRadar();
  } catch (_) {}
}

function openModal(id) {
  const el = $(id);
  if (el) el.classList.add("open");
}

function closeModal(id) {
  const el = $(id);
  if (el) el.classList.remove("open");
}

function wireModals() {
  on("btn-remote", "click", () => openModal("modal-remote"));
  on("btn-talk", "click", () => openModal("modal-talk"));
  on("btn-camera", "click", () => openModal("modal-camera"));
  on("profile-card", "click", () => {
    updateProfileModal();
    openModal("modal-profile");
  });
  on("gear-btn", "click", () => openModal("modal-settings"));

  on("close-remote", "click", () => closeModal("modal-remote"));
  on("close-talk", "click", () => closeModal("modal-talk"));
  on("close-camera", "click", () => closeModal("modal-camera"));
  on("close-profile", "click", () => closeModal("modal-profile"));
  on("close-settings", "click", () => closeModal("modal-settings"));

  document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) backdrop.classList.remove("open");
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.open").forEach((m) => m.classList.remove("open"));
    }
  });
}

const activeDirections = new Set();

function wireRemoteControl() {
  const buttons = document.querySelectorAll(".dpad-btn");

  buttons.forEach((btn) => {
    const dir = btn.dataset.dir;

    btn.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      btn.classList.add("pressed");
      activeDirections.add(dir);
      sendControl(dir, true);
      updateControlDisplay();
    });

    btn.addEventListener("pointerup", (e) => {
      e.preventDefault();
      btn.classList.remove("pressed");
      activeDirections.delete(dir);
      sendControl(dir, false);
      updateControlDisplay();
    });

    btn.addEventListener("pointerleave", () => {
      if (btn.classList.contains("pressed")) {
        btn.classList.remove("pressed");
        activeDirections.delete(dir);
        sendControl(dir, false);
        updateControlDisplay();
      }
    });
  });

  const keyMap = {
    ArrowUp: "forward",
    ArrowDown: "backward",
    ArrowLeft: "left",
    ArrowRight: "right",
    w: "forward",
    s: "backward",
    a: "left",
    d: "right"
  };

  document.addEventListener("keydown", (e) => {
    if (!$("modal-remote").classList.contains("open")) return;
    const dir = keyMap[e.key];
    if (!dir) return;
    const btn = document.querySelector(`[data-dir="${dir}"]`);
    if (btn && !btn.classList.contains("pressed")) {
      btn.classList.add("pressed");
      activeDirections.add(dir);
      sendControl(dir, true);
      updateControlDisplay();
    }
  });

  document.addEventListener("keyup", (e) => {
    if (!$("modal-remote").classList.contains("open")) return;
    const dir = keyMap[e.key];
    if (!dir) return;
    const btn = document.querySelector(`[data-dir="${dir}"]`);
    if (btn) {
      btn.classList.remove("pressed");
      activeDirections.delete(dir);
      sendControl(dir, false);
      updateControlDisplay();
    }
  });
}

async function sendControl(direction, pressed) {
  try {
    await fetch(`${API}/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction, pressed })
    });
  } catch (_) {}
}

function updateControlDisplay() {
  const status = $("control-status-text");
  const dot = $("control-status-dot");
  if (status) {
    if (activeDirections.size > 0) {
      const dirs = Array.from(activeDirections).map((d) => d.toUpperCase()).join(", ");
      status.textContent = `Moving: ${dirs}`;
      if (dot) {
        dot.style.background = "#00f0c0";
        dot.style.boxShadow = "0 0 10px #00f0c0";
      }
    } else {
      status.textContent = "Ready";
      if (dot) {
        dot.style.background = "var(--gold)";
        dot.style.boxShadow = "0 0 8px var(--gold)";
      }
    }
  }
}

let voiceRunning = false;

function wireVoice() {
  on("start-voice-btn", "click", startVoice);
  on("stop-voice-btn", "click", stopVoice);

  setInterval(() => {
    if ($("modal-talk").classList.contains("open")) {
      checkVoiceStatus();
    }
  }, 3000);
}

async function startVoice() {
  try {
    const res = await fetch(`${API}/voice/start`, { method: "POST" });
    const data = await res.json();
    if (data.status === "started" || data.status === "already_running") {
      setVoiceRunning(true);
      showToast("🎙️ Voice started!");
    } else {
      showToast("⚠️ Could not start voice", true);
    }
  } catch (_) {
    showToast("⚠️ Backend not reachable", true);
  }
}

async function stopVoice() {
  try {
    await fetch(`${API}/voice/stop`, { method: "POST" });
    setVoiceRunning(false);
    showToast("⏹ Voice stopped");
  } catch (_) {
    setVoiceRunning(false);
  }
}

async function checkVoiceStatus() {
  try {
    const res = await fetch(`${API}/voice/status`);
    const data = await res.json();
    if (data.running !== voiceRunning) setVoiceRunning(data.running);
  } catch (_) {}
}

function setVoiceRunning(running) {
  voiceRunning = running;
  const startBtn = $("start-voice-btn");
  const stopBtn = $("stop-voice-btn");
  const status = $("vs-status");
  const indicator = $("vs-indicator");
  const pulse = $("speech-pulse");

  if (startBtn) startBtn.disabled = running;
  if (stopBtn) stopBtn.disabled = !running;
  if (status) status.textContent = running ? "Listening… 🎙️" : "Stopped";
  if (indicator) indicator.classList.toggle("on", running);
  if (pulse) pulse.classList.toggle("active", running);
}

let cameraRunning = false;
let cameraPollTimer = null;

function wireCamera() {
  on("start-camera-btn", "click", startCamera);
  on("stop-camera-btn", "click", stopCamera);

  setInterval(() => {
    if ($("modal-camera") && $("modal-camera").classList.contains("open")) {
      checkCameraStatus();
    }
  }, 1800);
}

async function startCamera() {
  try {
    const res = await fetch(`${API}/camera/start`, { method: "POST" });
    const data = await res.json();
    if (data.status === "started" || data.status === "already_running") {
      setCameraRunning(true);
      showToast("📷 Live AI Vision started!");
    } else {
      showToast("⚠️ Could not start camera", true);
    }
  } catch (_) {
    showToast("⚠️ Backend not reachable", true);
  }
}

async function stopCamera() {
  try {
    await fetch(`${API}/camera/stop`, { method: "POST" });
    setCameraRunning(false);
    showToast("📷 Vision stopped");
  } catch (_) {
    setCameraRunning(false);
  }
}

async function checkCameraStatus() {
  try {
    const res = await fetch(`${API}/camera/status`);
    const data = await res.json();
    if (data.running !== cameraRunning) {
      setCameraRunning(data.running);
    }
    if (data.running) {
      updateCameraTelemetry(data);
    }
  } catch (_) {}
}

function setCameraRunning(running) {
  cameraRunning = running;
  const startBtn = $("start-camera-btn");
  const stopBtn = $("stop-camera-btn");
  const led = $("cam-led");
  const text = $("cam-status-text");
  const feed = $("camera-feed");
  const hud = $("hud-overlay");
  const placeholder = $("camera-placeholder");
  const fpsPill = $("cam-fps-pill");

  if (startBtn) startBtn.disabled = running;
  if (stopBtn) stopBtn.disabled = !running;
  if (led) led.classList.toggle("on", running);
  if (text) text.textContent = running ? "Live AI Vision Stream" : "Camera is Off";
  if (fpsPill) fpsPill.style.display = running ? "block" : "none";

  if (running) {
    if (feed) {
      const streamUrl = `${window.location.origin}/video_feed?t=${Date.now()}`;
      feed.src = streamUrl;
      feed.style.display = "block";
    }
    if (hud) hud.style.display = "block";
    if (placeholder) placeholder.style.display = "none";

    if (!cameraPollTimer) {
      cameraPollTimer = setInterval(checkCameraStatus, 1000);
    }
  } else {
    if (feed) {
      feed.src = "";
      feed.style.display = "none";
    }
    if (hud) hud.style.display = "none";
    if (placeholder) placeholder.style.display = "flex";

    if (cameraPollTimer) {
      clearInterval(cameraPollTimer);
      cameraPollTimer = null;
    }

    resetCameraTelemetry();
  }
}

function updateCameraTelemetry(data) {
  const fpsNum = $("cam-fps-num");
  if (fpsNum && data.fps !== undefined) {
    fpsNum.textContent = data.fps;
  }

  const objList = $("detected-objects-list");
  if (objList) {
    const objects = data.objects || [];
    if (objects.length > 0) {
      const counts = {};
      objects.forEach((o) => {
        counts[o] = (counts[o] || 0) + 1;
      });
      objList.innerHTML = Object.entries(counts)
        .map(([name, count]) => `<span class="meta-chip meta-obj">${name.toUpperCase()}${count > 1 ? ` (${count})` : ""}</span>`)
        .join("");
    } else {
      objList.innerHTML = '<span class="meta-chip meta-empty">None detected</span>';
    }
  }

  const faceList = $("detected-faces-list");
  if (faceList) {
    const faces = data.faces || [];
    if (faces.length > 0) {
      faceList.innerHTML = faces
        .map((f) => `<span class="meta-chip meta-face">👤 ${f.toUpperCase()}</span>`)
        .join("");
    } else {
      faceList.innerHTML = '<span class="meta-chip meta-empty">Searching…</span>';
    }
  }
}

function resetCameraTelemetry() {
  const fpsNum = $("cam-fps-num");
  if (fpsNum) fpsNum.textContent = "0";

  const objList = $("detected-objects-list");
  if (objList) objList.innerHTML = '<span class="meta-chip meta-empty">None detected</span>';

  const faceList = $("detected-faces-list");
  if (faceList) faceList.innerHTML = '<span class="meta-chip meta-empty">Searching…</span>';
}

function updateProfileModal() {
  if ($("modal-name")) $("modal-name").textContent = appState.name;
  if ($("modal-title-text")) $("modal-title-text").textContent = appState.title;
  if ($("modal-level")) $("modal-level").textContent = appState.level;
  if ($("modal-level2")) $("modal-level2").textContent = appState.level;
  if ($("modal-coins")) $("modal-coins").textContent = appState.coins;
}

function wireCoins() {
  on("coins-plus-btn", "click", () => {
    const reward = Math.floor(10 + Math.random() * 30);
    appState.coins += reward;
    if ($("coins-count")) $("coins-count").textContent = appState.coins;
    showToast(`🪙 +${reward} Coins!`);
    fetch(`${API}/profile/coins`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delta: reward })
    }).catch(() => {});
  });
}

function wireSettings() {
  document.querySelectorAll(".mood-opt").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mood-opt").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  on("save-settings-btn", "click", () => {
    const name = ($("set-username") || {}).value || appState.name;
    const title = ($("set-title") || {}).value || appState.title;
    const moodBtn = document.querySelector(".mood-opt.active");
    const mood = moodBtn ? moodBtn.dataset.mood : appState.mood.mood;

    appState.name = name;
    appState.title = title;
    appState.mood.mood = mood;

    if ($("user-name")) $("user-name").textContent = name;
    if ($("user-title")) $("user-title").textContent = title;

    updateMoodDisplay();

    fetch(`${API}/mood`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mood })
    }).catch(() => {});

    showToast("💾 Settings saved!");
    closeModal("modal-settings");
  });
}

function wireCharacterClick() {
  const pippo = $("pippo-character");
  if (!pippo) return;

  const quips = [
    "Namaste Dost! 🙏",
    "Hehe, Pippo is ready! 🤖",
    "Let's play and explore! 🚀",
    "Mera dost Prakhar! ❤️"
  ];
  let idx = 0;

  pippo.addEventListener("click", () => {
    showToast(quips[idx % quips.length]);
    idx++;
  });
}

function showToast(msg, isError = false) {
  const container = $("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  if (isError) toast.style.borderColor = "#ff4444";
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 2900);
}

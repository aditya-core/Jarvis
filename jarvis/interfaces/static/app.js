"use strict";

/* ============ boot sequence ============ */
const bootLines = [
  "INITIALIZING CORE SYSTEMS..........",
  "LOADING NEURAL BRAIN MODULE.......",
  "SYNCING LONG-TERM MEMORY..........",
  "LAUNCHING INTERFACE................",
];
const boot = document.getElementById('boot');
const bootLinesEl = document.getElementById('boot-lines');
let bootIdx = 0;
function bootTick() {
  if (bootIdx >= bootLines.length) {
    boot.classList.add('done');
    setTimeout(() => { boot.style.display = 'none'; wake(); }, 900);
    return;
  }
  const div = document.createElement('div');
  div.className = 'boot-line';
  div.textContent = bootLines[bootIdx];
  bootLinesEl.appendChild(div);
  bootIdx++;
  setTimeout(bootTick, 420);
}
bootTick();

/* ============ particle field ============ */
const cv = document.getElementById('particles'), ctx = cv.getContext('2d');
let pts = [];
function initPts() {
  pts = [];
  const n = Math.min(90, Math.floor(innerWidth * innerHeight / 22000));
  for (let i = 0; i < n; i++) pts.push({
    x: Math.random() * cv.width, y: Math.random() * cv.height,
    vx: (Math.random() - .5) * .35, vy: (Math.random() - .5) * .35
  });
}
function resize() { cv.width = innerWidth; cv.height = innerHeight; initPts(); }
function drawParticles() {
  ctx.clearRect(0, 0, cv.width, cv.height);
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0 || p.x > cv.width) p.vx *= -1;
    if (p.y < 0 || p.y > cv.height) p.vy *= -1;
    ctx.fillStyle = 'rgba(34,211,238,.65)';
    ctx.beginPath(); ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2); ctx.fill();
    for (let j = i + 1; j < pts.length; j++) {
      const q = pts[j], dx = p.x - q.x, dy = p.y - q.y, d = Math.hypot(dx, dy);
      if (d < 120) {
        ctx.strokeStyle = `rgba(34,211,238,${(1 - d / 120) * 0.25})`;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
      }
    }
  }
  requestAnimationFrame(drawParticles);
}
resize(); drawParticles();
addEventListener('resize', resize);

/* ============ helpers ============ */
const $ = id => document.getElementById(id);
function wake() {
  const r = document.createElement('div');
  r.className = 'ripple-ring';
  document.getElementById('ripple').appendChild(r);
  setTimeout(() => r.remove(), 1700);
}
function fmtUptime(s) {
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}
async function api(path, opts) {
  const res = await fetch(path, opts);
  return res.json();
}
function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* ============ status polling ============ */
async function pollStatus() {
  try {
    const s = await api('/api/status');
    const brain = $('chip-brain');
    brain.textContent = 'BRAIN ' + (s.brain ? '● ONLINE' : '○ OFFLINE');
    brain.classList.toggle('off', !s.brain);
    $('chip-activity').textContent = 'ACTIVITY ' + s.activity_count;
    $('chip-uptime').textContent = 'UPTIME ' + fmtUptime(s.uptime);
  } catch (e) {}
}
function tickClock() {
  $('chip-clock').textContent = new Date().toTimeString().slice(0, 8);
}
setInterval(pollStatus, 4000);
setInterval(tickClock, 1000);

/* ============ activity feed ============ */
let lastActivityTs = '';
async function pollActivity() {
  try {
    const items = await api('/api/activity');
    if (!items.length) return;
    const latest = items[0];
    if (latest.ts === lastActivityTs) return;
    lastActivityTs = latest.ts;
    const feed = $('activity');
    for (const it of items.slice(0, 20)) {
      if (feed.querySelector(`[data-ts="${it.ts}"]`)) continue;
      feed.insertAdjacentHTML('afterbegin', activityItem(it));
    }
    while (feed.children.length > 60) feed.lastChild.remove();
  } catch (e) {}
}
function activityItem(it) {
  const t = it.ts ? it.ts.slice(11, 16) : '--:--';
  const reply = (it.reply || '').replace(/\n/g, ' ').slice(0, 110);
  return `<div class="feed-item" data-ts="${it.ts || ''}">
    <div class="feed-time">${t}</div>
    <div class="feed-user">${escapeHtml(it.user)}</div>
    <div class="feed-reply">${escapeHtml(reply)}</div>
    <div class="feed-meta">${it.intent || 'unknown'} · ${Math.round((it.confidence || 0) * 100)}%</div>
  </div>`;
}
setInterval(pollActivity, 2500);
pollActivity();

/* ============ AI thinking ============ */
async function pollThinking() {
  try {
    const t = await api('/api/thinking');
    if (!t || !t.intent) return;
    $('thinking').innerHTML = `
      <div class="think-row"><span>intent</span><b>${t.intent}</b></div>
      <div class="think-row"><span>confidence</span><b>${Math.round((t.confidence || 0) * 100)}%</b></div>
      <div class="think-row"><span>plugin</span><b>${t.plugin || 'none'}</b></div>
      <div class="think-row"><span>llm</span><b>${t.llm_consulted ? 'yes' : 'no'}</b></div>
      <div class="think-row"><span>matched</span><b>${escapeHtml((t.matched || []).join(', ') || '—')}</b></div>
      <div class="think-row"><span>entity</span><b>${escapeHtml(t.entity || '—')}</b></div>`;
  } catch (e) {}
}
setInterval(pollThinking, 2500);
pollThinking();

/* ============ memory & system ============ */
async function pollMemory() {
  try {
    const m = await api('/api/memory');
    $('memory').innerHTML = `
      <div class="stat"><span>conversations</span><b>${m.conversation_turns}</b></div>
      <div class="stat"><span>notes</span><b>${m.notes}</b></div>
      <div class="stat"><span>profile facts</span><b>${m.profile_facts}</b></div>
      <div class="stat"><span>memory file</span><b>${m.memory_kb} KB</b></div>`;
  } catch (e) {}
}
async function pollSystem() {
  try {
    const s = await api('/api/system');
    $('system').innerHTML = `
      <div class="bar"><span>CPU</span><i style="width:${Math.round(s.cpu)}%"></i><b>${Math.round(s.cpu)}%</b></div>
      <div class="bar"><span>RAM</span><i style="width:${Math.round(s.ram_pct)}%"></i><b>${Math.round(s.ram_pct)}%</b></div>
      <div class="bar"><span>DISK</span><i style="width:${Math.round(s.disk_pct)}%"></i><b>${Math.round(s.disk_pct)}%</b></div>
      <div class="stat"><span>ram</span><b>${s.ram_gb} GB</b></div>
      <div class="stat"><span>disk</span><b>${s.disk_gb} GB</b></div>`;
  } catch (e) {}
}
setInterval(pollMemory, 5000);
setInterval(pollSystem, 5000);
pollMemory();
pollSystem();

/* ============ command ============ */
async function sendCommand(text) {
  text = (text || '').trim();
  if (!text) return;
  $('cmd-input').value = '';
  const reactor = $('reactor');
  reactor.classList.add('thinking');
  $('reply').innerHTML = '<span class="typing">> processing...</span>';
  try {
    const r = await api('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    reactor.classList.remove('thinking');
    wake();
    typeWriter('> ' + r.reply, $('reply'));
    pollActivity();
    pollThinking();
    pollMemory();
    pollStatus();
  } catch (e) {
    reactor.classList.remove('thinking');
    $('reply').innerHTML = '<span class="err">> connection error</span>';
  }
}
function typeWriter(text, el) {
  el.textContent = '';
  if (text.length > 260) { el.textContent = text; return; }
  let i = 0;
  el.classList.add('typing');
  const t = setInterval(() => {
    el.textContent = text.slice(0, ++i);
    if (i >= text.length) { clearInterval(t); el.classList.remove('typing'); }
  }, 14);
}
$('send-btn').addEventListener('click', () => sendCommand($('cmd-input').value));
$('cmd-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendCommand(e.target.value);
});

/* ============ browser voice ============ */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  let recog;
  $('voice-btn').addEventListener('click', () => {
    if (!recog) {
      recog = new SR();
      recog.lang = 'en-US';
      recog.interimResults = false;
      recog.onresult = e => sendCommand(e.results[0][0].transcript);
      recog.onend = () => $('voice-btn').classList.remove('active');
      recog.onerror = () => {
        $('voice-btn').classList.remove('active');
        $('reply').innerHTML = '<span class="err">> voice error — try again</span>';
      };
    }
    recog.start();
    $('voice-btn').classList.add('active');
  });
} else {
  $('voice-btn').addEventListener('click', () =>
    alert('Browser voice needs Chrome/Edge.\nFor offline voice use: python main.py --voice'));
}

/* ============ fullscreen ============ */
$('fullscreen-btn').addEventListener('click', () => {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen();
  else document.exitFullscreen();
});
document.addEventListener('keydown', e => {
  if (e.key === 'f' || e.key === 'F') $('fullscreen-btn').click();
});

pollStatus();
tickClock();

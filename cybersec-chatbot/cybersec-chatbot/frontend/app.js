/**
 * app.js — CyberGuard frontend logic.
 *
 * Responsibilities:
 *  - Tab switching
 *  - Chat: send messages, render replies with threat badges
 *  - Threat analyzer: POST /analyze, render results
 *  - Password checker: POST /analyze/password with live feedback
 */

const API_BASE = "http://localhost:8000";

// Generate a stable session ID for this browser tab.
const SESSION_ID = (() => {
  const stored = sessionStorage.getItem("cg_session");
  if (stored) return stored;
  const id = crypto.randomUUID();
  sessionStorage.setItem("cg_session", id);
  return id;
})();

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(el => el.classList.remove("active"));
  const btn = document.getElementById(`tab-btn-${name}`);
  const panel = document.getElementById(`tab-${name}`);
  if (btn) btn.classList.add("active");
  if (panel) panel.classList.add("active");
}

// Ensure the first tab is active on page load
document.addEventListener("DOMContentLoaded", () => {
  // Find the first tab button with class 'tab'
  const firstTab = document.querySelector(".tab");
  if (firstTab) {
    const tabId = firstTab.id.replace("tab-btn-", "");
    switchTab(tabId);
  }
});

// ── Utilities ──────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setLoading(btnId, isLoading, label = "Send") {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = isLoading;
  btn.textContent = isLoading ? "…" : label;
}

// ── Chat ───────────────────────────────────────────────────────────────────
const messagesEl = document.getElementById("messages");
const chatInput  = document.getElementById("chat-input");
const charCount  = document.getElementById("char-count");

chatInput?.addEventListener("input", () => {
  charCount.textContent = chatInput.value.length;
});

function appendMessage(role, html, threatLevel = "safe") {
  const div = document.createElement("div");
  div.className = `msg ${role}`;

  if (role === "bot" && threatLevel !== "safe") {
    div.classList.add(`threat-${threatLevel}`);
    const badge = `<span class="threat-badge badge-${threatLevel}">${threatLevel}</span><br>`;
    div.innerHTML = `<div class="bot-label">CyberGuard</div>${badge}${html}`;
  } else if (role === "bot") {
    div.innerHTML = `<div class="bot-label">CyberGuard</div>${html}`;
  } else {
    div.textContent = html; // user input — never render raw HTML
  }

  messagesEl.appendChild(div);
  div.scrollIntoView({ behavior: "smooth" });
  return div;
}

async function sendChat() {
  const message = chatInput.value.trim();
  if (!message) return;

  chatInput.value = "";
  charCount.textContent = "0";
  appendMessage("user", message);

  const loader = appendMessage("bot", "Thinking…");
  loader.classList.add("loading");
  setLoading("send-btn", true);

  try {
    const res = await fetch(`${API_BASE}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: SESSION_ID,
        message,
        include_threat_analysis: true,
      }),
    });

    const data = await res.json();
    loader.remove();

    if (!res.ok) {
      appendMessage("bot", `⚠️ Server error: ${escapeHtml(data.detail || "Unknown error")}`);
      return;
    }

    // Format threat flags and type badge if present
    let flagsHtml = "";
    if (data.threat_level !== "safe") {
      const threatTypeEmojis = {
        phishing: "🎣",
        malware: "🦠",
        ransomware: "🔐",
        mitm: "🔗",
        ddos: "⚡",
        social_engineering: "🎭",
        sql_injection: "💉",
        xss: "⚙️",
        brute_force: "🔨",
        zero_day: "💣",
        suspicious_activity: "⚠️",
        unknown: "❓",
      };
      const threatTypeNames = {
        phishing: "Phishing",
        malware: "Malware",
        ransomware: "Ransomware",
        mitm: "MITM",
        ddos: "DDoS",
        social_engineering: "Social Eng.",
        sql_injection: "SQL Injection",
        xss: "XSS",
        brute_force: "Brute Force",
        zero_day: "Zero-Day",
        suspicious_activity: "Suspicious",
      };
      const emoji = threatTypeEmojis[data.threat_type] || "⚠️";
      const threatName = threatTypeNames[data.threat_type] || data.threat_type;
      
      flagsHtml = `<div style="background:rgba(255,68,68,0.1);border-left:3px solid #ff4444;padding:10px;margin-top:12px;border-radius:6px">
        <div style="font-weight:700;color:#ff4444;margin-bottom:6px">${emoji} ${threatName} Detected</div>`;
      
      if (data.threat_flags && data.threat_flags.length > 0) {
        flagsHtml += `<ul style="margin:0;padding-left:18px;font-size:12px;color:#ffa0a0">
          ${data.threat_flags.map(f => `<li>${escapeHtml(f)}</li>`).join("")}
        </ul>`;
      }
      flagsHtml += `</div>`;
    }

    appendMessage("bot", escapeHtml(data.reply) + flagsHtml, data.threat_level);

  } catch (err) {
    loader.remove();
    appendMessage("bot", "⚠️ Could not reach the server. Is the backend running on port 8000?");
  } finally {
    setLoading("send-btn", false, "Send");
    chatInput.focus();
  }
}

// ── Threat Analyzer ────────────────────────────────────────────────────────
async function analyzeText() {
  const text = document.getElementById("analyze-input").value.trim();
  if (!text) return;

  const resultEl = document.getElementById("analyze-result");
  resultEl.classList.remove("hidden");
  resultEl.innerHTML = "<em>Analysing…</em>";

  try {
    const res = await fetch(`${API_BASE}/analyze/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const d = await res.json();

    const levelColors = {
      safe:       "#00ff88",
      suspicious: "#ffd700",
      critical:   "#ff4444",
    };
    const color = levelColors[d.threat_level] || "#8b949e";
    const confidencePct = Math.round(d.confidence * 100);
    
    // Map threat types to emojis and descriptions
    const threatTypeEmojis = {
      phishing: "🎣",
      malware: "🦠",
      ransomware: "🔐",
      mitm: "🔗",
      ddos: "⚡",
      social_engineering: "🎭",
      sql_injection: "💉",
      xss: "⚙️",
      brute_force: "🔨",
      zero_day: "💣",
      suspicious_activity: "⚠️",
      unknown: "❓",
      none: "✅",
    };
    
    const threatTypeNames = {
      phishing: "Phishing Attack",
      malware: "Malware",
      ransomware: "Ransomware",
      mitm: "Man-in-the-Middle",
      ddos: "DDoS Attack",
      social_engineering: "Social Engineering",
      sql_injection: "SQL Injection",
      xss: "Cross-Site Scripting (XSS)",
      brute_force: "Brute Force Attack",
      zero_day: "Zero-Day Vulnerability",
      suspicious_activity: "Suspicious Activity",
      unknown: "Unknown Threat",
      none: "Safe",
    };
    
    const emoji = threatTypeEmojis[d.threat_type] || "❓";
    const threatName = threatTypeNames[d.threat_type] || d.threat_type;

    const patternList = d.detected_patterns.length
      ? d.detected_patterns.map(p => `<li>${escapeHtml(p)}</li>`).join("")
      : "<li>None detected</li>";

    const aiSection = d.ai_analysis
      ? `<hr style="border-color:rgba(0,212,255,0.2);margin:12px 0">
         <strong>🤖 AI Analysis:</strong>
         <p style="margin-top:6px;font-style:italic">${escapeHtml(d.ai_analysis)}</p>`
      : "";

    resultEl.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <span style="font-size:32px">${emoji}</span>
        <div>
          <h3 style="color:${color};margin:0;text-transform:uppercase">${threatName}</h3>
          <p style="color:#8b949e;margin:4px 0 0;font-size:12px">${d.threat_level.toUpperCase()} SEVERITY</p>
        </div>
      </div>
      
      <div style="margin:14px 0">
        <div style="font-size:12px;color:#8b949e;margin-bottom:6px;font-weight:600">CONFIDENCE: ${confidencePct}%</div>
        <div class="strength-track">
          <div class="strength-fill" style="width:${confidencePct}%;background:${color}"></div>
        </div>
      </div>
      
      <strong style="color:#00d4ff">🔍 Detected Patterns:</strong>
      <ul style="margin:8px 0 14px;padding-left:18px">${patternList}</ul>
      
      <strong style="color:#00d4ff">💡 Action Required:</strong>
      <p style="margin-top:8px;line-height:1.6">${escapeHtml(d.advice)}</p>
      ${aiSection}
    `;
  } catch (err) {
    resultEl.innerHTML = "⚠️ Failed to reach the analysis endpoint.";
  }
}

// ── Password Checker ───────────────────────────────────────────────────────
let pwDebounceTimer;

function checkPassword() {
  clearTimeout(pwDebounceTimer);
  pwDebounceTimer = setTimeout(_doCheckPassword, 300); // debounce 300ms
}

async function _doCheckPassword() {
  const pw = document.getElementById("pw-input").value;
  const resultEl = document.getElementById("pw-result");

  if (!pw) {
    resultEl.classList.add("hidden");
    return;
  }
  resultEl.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/analyze/password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pw }),
    });
    const d = await res.json();

    const strengthColors = {
      very_weak:  "#f85149",
      weak:       "#e3a84d",
      moderate:   "#d29922",
      strong:     "#3fb950",
      very_strong:"#58a6ff",
    };
    const color = strengthColors[d.strength] || "#8b949e";
    const label = d.strength.replace("_", " ");

    const issuesList = d.issues.length
      ? `<strong>Issues:</strong><ul style="margin:6px 0 10px;padding-left:18px">
          ${d.issues.map(i => `<li>⚠️ ${escapeHtml(i)}</li>`).join("")}
        </ul>`
      : `<p style="color:#3fb950;margin-bottom:10px">✅ No common weaknesses detected.</p>`;

    const tipsList = d.suggestions.length
      ? `<strong>Tips:</strong><ul style="margin:6px 0;padding-left:18px">
          ${d.suggestions.map(s => `<li>💡 ${escapeHtml(s)}</li>`).join("")}
        </ul>`
      : "";

    resultEl.innerHTML = `
      <h3 style="color:${color};text-transform:capitalize;margin-bottom:4px">
        ${label}
        <span style="font-weight:400;font-size:13px;color:#8b949e"> — ${d.score}/100</span>
      </h3>
      <div style="font-size:12px;color:#8b949e;margin-bottom:4px">Strength</div>
      <div class="strength-track">
        <div class="strength-fill" style="width:${d.score}%;background:${color}"></div>
      </div>
      <p style="font-size:12px;color:#8b949e;margin-bottom:12px">
        Entropy: ${d.entropy_bits} bits
      </p>
      ${issuesList}
      ${tipsList}
    `;
  } catch (err) {
    resultEl.innerHTML = "⚠️ Could not reach the server.";
  }
}

function togglePwVisibility() {
  const input = document.getElementById("pw-input");
  input.type = input.type === "password" ? "text" : "password";
}

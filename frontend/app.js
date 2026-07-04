"use strict";

const feedEl = document.getElementById("feed");
const feedEmptyEl = document.getElementById("feed-empty");
const goalTextEl = document.getElementById("goal-text");
const successSignalEl = document.getElementById("success-signal");
const reviewCadenceEl = document.getElementById("review-cadence");
const inputEl = document.getElementById("checkin-input");
const sendBtn = document.getElementById("send-btn");
const errorEl = document.getElementById("composer-error");

function fmtDate(iso) {
  const d = new Date(iso + "T00:00:00Z");
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function renderCheckin(c) {
  const day = el("article", "day");
  day.appendChild(el("div", "day__date", fmtDate(c.date)));

  const userBubble = el("div", "bubble bubble--user");
  userBubble.appendChild(el("div", "bubble__who", "You"));
  userBubble.appendChild(el("div", "bubble__text", c.checkin_text));
  day.appendChild(userBubble);

  const isPattern = !!c.pattern_detected;
  const agentBubble = el("div", "bubble bubble--agent" + (isPattern ? " bubble--pattern" : ""));
  if (isPattern) {
    agentBubble.appendChild(el("div", "pattern-badge", "Pattern detected"));
  }
  agentBubble.appendChild(el("div", "bubble__who", "The Mirror"));
  agentBubble.appendChild(el("div", "bubble__text", c.agent_response));
  if (isPattern && c.pattern_description) {
    const desc = el("div", "pattern-desc");
    desc.appendChild(el("strong", null, "Evidence: "));
    desc.appendChild(document.createTextNode(c.pattern_description));
    agentBubble.appendChild(desc);
  }
  day.appendChild(agentBubble);
  return day;
}

function scrollToBottom() {
  feedEl.scrollTop = feedEl.scrollHeight;
}

function renderGoal(goal) {
  if (!goal) return;
  goalTextEl.textContent = goal.goal_text;
  successSignalEl.textContent = goal.success_signal;
  reviewCadenceEl.textContent = goal.review_cadence;
}

async function loadHistory() {
  const res = await fetch("/history");
  if (!res.ok) throw new Error("Failed to load history");
  const data = await res.json();
  renderGoal(data.goal);
  feedEl.innerHTML = "";
  if (!data.checkins || data.checkins.length === 0) {
    feedEl.appendChild(el("div", "feed__empty", "No check-ins yet."));
    return;
  }
  for (const c of data.checkins) feedEl.appendChild(renderCheckin(c));
  scrollToBottom();
}

function showTyping() {
  const day = el("article", "day");
  day.id = "typing-indicator";
  const bubble = el("div", "bubble bubble--agent");
  bubble.appendChild(el("div", "bubble__who", "The Mirror"));
  const typing = el("div", "typing");
  typing.appendChild(el("span"));
  typing.appendChild(el("span"));
  typing.appendChild(el("span"));
  bubble.appendChild(typing);
  day.appendChild(bubble);
  feedEl.appendChild(day);
  scrollToBottom();
}

function removeTyping() {
  const t = document.getElementById("typing-indicator");
  if (t) t.remove();
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  inputEl.disabled = busy;
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.hidden = false;
}
function clearError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

async function submitCheckin() {
  const text = inputEl.value.trim();
  if (!text) return;
  clearError();
  setBusy(true);

  // Optimistically show the user's message immediately.
  const optimistic = el("article", "day");
  optimistic.appendChild(el("div", "day__date", fmtDate(new Date().toISOString().slice(0, 10))));
  const ub = el("div", "bubble bubble--user");
  ub.appendChild(el("div", "bubble__who", "You"));
  ub.appendChild(el("div", "bubble__text", text));
  optimistic.appendChild(ub);
  feedEl.appendChild(optimistic);
  inputEl.value = "";
  autoGrow();
  showTyping();

  try {
    const res = await fetch("/checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checkin_text: text }),
    });
    removeTyping();
    optimistic.remove();
    if (!res.ok) {
      let detail = "The coach couldn't respond. Please try again.";
      try {
        const err = await res.json();
        if (err.detail) detail = "Error: " + err.detail;
      } catch (_) {}
      // Restore the message so it isn't lost.
      inputEl.value = text;
      showError(detail);
      return;
    }
    const row = await res.json();
    feedEl.appendChild(renderCheckin(row));
    scrollToBottom();
  } catch (e) {
    removeTyping();
    optimistic.remove();
    inputEl.value = text;
    showError("Network error - could not reach the server.");
  } finally {
    setBusy(false);
    inputEl.focus();
  }
}

function autoGrow() {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + "px";
}

sendBtn.addEventListener("click", submitCheckin);
inputEl.addEventListener("input", autoGrow);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitCheckin();
  }
});

loadHistory().catch((e) => {
  feedEl.innerHTML = "";
  feedEl.appendChild(el("div", "feed__empty", "Failed to load. Is the backend running?"));
  console.error(e);
});

const state = {
  config: null,
  lastToolPayload: null,
};

const els = {
  health: document.querySelector("#health"),
  mode: document.querySelector("#mode"),
  region: document.querySelector("#region"),
  lambdaName: document.querySelector("#lambdaName"),
  alarmCount: document.querySelector("#alarmCount"),
  alarmList: document.querySelector("#alarmList"),
  transcript: document.querySelector("#transcript"),
  message: document.querySelector("#message"),
  toolOutput: document.querySelector("#toolOutput"),
};

async function requestJson(path, body) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || response.statusText);
  }
  return payload;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setBusy(form, busy) {
  for (const button of form.querySelectorAll("button")) {
    button.disabled = busy;
  }
}

function addBubble(role, message, options = {}) {
  const severity = options.severity ? ` severity-${options.severity}` : "";
  const article = document.createElement("article");
  article.className = `bubble ${role}${options.error ? " error" : ""}${severity}`;
  article.innerHTML = `
    <span class="bubble-role">${escapeHtml(role === "user" ? "You" : "Agent")}</span>
    <p>${escapeHtml(message)}</p>
    ${options.actions?.length ? `<ul class="actions">${options.actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
    ${options.raw ? `<pre>${escapeHtml(JSON.stringify(options.raw, null, 2))}</pre>` : ""}
  `;
  els.transcript.appendChild(article);
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function renderToolOutput(title, payload) {
  state.lastToolPayload = payload;
  els.toolOutput.textContent = `${title}\n\n${JSON.stringify(payload, null, 2)}`;
  showView("tools");
}

function renderAlarms(payload) {
  els.alarmCount.textContent = String(payload.count ?? 0);
  if (!payload.alarms?.length) {
    els.alarmList.innerHTML = `<span class="muted">No active alarms reported.</span>`;
    return;
  }
  els.alarmList.innerHTML = payload.alarms
    .map(
      (alarm) => `
        <article class="alarm-item">
          <strong>${escapeHtml(alarm.name)}</strong>
          <span>${escapeHtml(alarm.reason || alarm.state || "ALARM")}</span>
        </article>
      `,
    )
    .join("");
}

function showView(name) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelector(`#view-${name}`).classList.add("active");
  document.querySelectorAll(".nav-btn").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === name);
  });
}

function fillRuntime(config) {
  els.mode.textContent = config.mode;
  els.region.textContent = config.region;
  els.lambdaName.textContent = config.iac_lambda_name;
  document.querySelector("#regionMetric").textContent = config.region;
  document.querySelector("#secretMetric").textContent = config.default_secret_name;
  document.querySelector("#secretName").value = config.default_secret_name;
  document.querySelector("#ctxMode").textContent = config.mode;
  document.querySelector("#ctxRegion").textContent = config.region;
  document.querySelector("#ctxLambda").textContent = config.iac_lambda_name;
  document.querySelector("#ctxSecret").textContent = config.default_secret_name;
  document.querySelector("#logGroups").innerHTML = Object.entries(config.log_groups || {})
    .map(([service, group]) => `<div class="log-row"><strong>${escapeHtml(service)}</strong><span>${escapeHtml(group)}</span></div>`)
    .join("");
}

async function loadRuntime() {
  try {
    const [health, config, alarms] = await Promise.all([requestJson("/health"), requestJson("/config"), requestJson("/alarms")]);
    state.config = config;
    els.health.textContent = health.status;
    els.health.className = "health ok";
    fillRuntime(config);
    renderAlarms(alarms);
  } catch (error) {
    els.health.textContent = "offline";
    els.health.className = "health bad";
    els.alarmList.innerHTML = `<span class="muted">${escapeHtml(error.message || "Unable to load alarms.")}</span>`;
  }
}

async function submitChat(message, form) {
  if (!message) {
    els.message.focus();
    return;
  }
  addBubble("user", message);
  setBusy(form, true);
  try {
    const payload = await requestJson("/chat", { message });
    addBubble("agent", payload.message || "Completed.", {
      severity: payload.severity,
      actions: payload.actions || [],
      raw: payload.raw && Object.keys(payload.raw).length ? payload.raw : null,
    });
    await refreshAlarmsOnly();
  } catch (error) {
    addBubble("agent", error.message || String(error), { error: true });
  } finally {
    setBusy(form, false);
  }
}

async function refreshAlarmsOnly() {
  try {
    renderAlarms(await requestJson("/alarms"));
  } catch {
    // Keep the previous alarm view if refresh fails during an investigation.
  }
}

document.querySelectorAll(".nav-btn").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

document.querySelector("#chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = els.message.value.trim();
  els.message.value = "";
  await submitChat(message, event.currentTarget);
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", async () => {
    const form = document.querySelector("#chatForm");
    showView("console");
    await submitChat(button.dataset.prompt, form);
  });
});

document.querySelector("#ssmForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  setBusy(form, true);
  try {
    const payload = await requestJson("/ssm/check", {
      target: document.querySelector("#ssmTarget").value.trim(),
      check_name: document.querySelector("#ssmCheck").value,
    });
    renderToolOutput("SSM Check", payload);
  } catch (error) {
    renderToolOutput("SSM Check Failed", { error: error.message || String(error) });
  } finally {
    setBusy(form, false);
  }
});

document.querySelector("#secretForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  setBusy(form, true);
  try {
    const payload = await requestJson("/secrets/validate", {
      secret_name: document.querySelector("#secretName").value.trim(),
    });
    renderToolOutput("Secret Policy", payload);
  } catch (error) {
    renderToolOutput("Secret Policy Failed", { error: error.message || String(error) });
  } finally {
    setBusy(form, false);
  }
});

document.querySelector("#iacForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  setBusy(form, true);
  try {
    const payload = await requestJson("/iac/invoke", {
      action: document.querySelector("#iacAction").value,
      environment: "dev",
      template: "quickslot-prod-like-dev",
      ttl_hours: Number(document.querySelector("#ttlHours").value || 24),
      variables: {},
    });
    renderToolOutput("IaC Request", payload);
  } catch (error) {
    renderToolOutput("IaC Request Failed", { error: error.message || String(error) });
  } finally {
    setBusy(form, false);
  }
});

document.querySelector("#clearBtn").addEventListener("click", () => {
  els.transcript.innerHTML = `
    <article class="bubble agent">
      <span class="bubble-role">Agent</span>
      <p>Console cleared. Send the next operational request.</p>
    </article>
  `;
});

loadRuntime();

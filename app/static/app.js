const state = {
  token: localStorage.getItem("airbnb_menage_token") || "",
  email: localStorage.getItem("airbnb_menage_email") || "",
  role: localStorage.getItem("airbnb_menage_role") || "",
  activeView: "dashboard",
  logements: [],
  reservations: [],
  missions: [],
  users: [],
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.remove("hidden");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.add("hidden"), 4200);
}

function parseJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    return JSON.parse(atob(padded));
  } catch {
    return {};
  }
}

function roleLabel(role) {
  return {
    admin: "Admin",
    proprietaire: "Proprietaire",
    responsable_conciergerie: "Responsable",
    agent_menage: "Agent menage",
  }[role] || "Utilisateur";
}

function canUseView(view) {
  if (!state.token) return false;
  if (state.role === "agent_menage") return ["dashboard", "missions"].includes(view);
  if (state.role === "proprietaire") return ["dashboard", "logements", "reservations", "missions"].includes(view);
  if (state.role === "responsable_conciergerie") return ["dashboard", "logements", "reservations", "missions"].includes(view);
  return true;
}

function canAssignMissions() {
  return ["admin", "responsable_conciergerie"].includes(state.role);
}

function canCreateUsers() {
  return state.role === "admin";
}

function canEditChecklist() {
  return ["admin", "responsable_conciergerie", "agent_menage"].includes(state.role);
}

function canReportIncidents() {
  return state.role === "agent_menage";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !(options.body instanceof FormData) && !(options.body instanceof URLSearchParams) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || "Action impossible");
  }
  return data;
}

function setSession(token, email) {
  const payload = parseJwtPayload(token);
  state.token = token;
  state.email = email;
  state.role = payload.role || "";
  localStorage.setItem("airbnb_menage_token", token);
  localStorage.setItem("airbnb_menage_email", email);
  localStorage.setItem("airbnb_menage_role", state.role);
  renderSession();
}

function clearSession() {
  state.token = "";
  state.email = "";
  state.role = "";
  localStorage.removeItem("airbnb_menage_token");
  localStorage.removeItem("airbnb_menage_email");
  localStorage.removeItem("airbnb_menage_role");
  renderSession();
}

function renderSession() {
  if (state.token && !state.role) {
    state.role = parseJwtPayload(state.token).role || "";
  }
  $("#sessionLabel").textContent = state.token ? `${state.email} - ${roleLabel(state.role)}` : "Non connecte";
  $("#authPanel").classList.toggle("hidden", Boolean(state.token));
  $("#workspace").classList.toggle("hidden", !state.token);
  $("#logoutBtn").classList.toggle("hidden", !state.token);
  applyRoleNavigation();
}

function applyRoleNavigation() {
  $$(".nav-btn").forEach((button) => {
    button.classList.toggle("hidden", !canUseView(button.dataset.view));
  });

  if (state.token && !canUseView(state.activeView)) {
    const firstAvailable = $$(".nav-btn").find((button) => !button.classList.contains("hidden"));
    if (firstAvailable) state.activeView = firstAvailable.dataset.view;
  }
}

function fmtDate(value) {
  if (!value) return "Non planifie";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function optionList(items, selected = "") {
  return items
    .map((item) => `<option value="${item.id}" ${item.id === selected ? "selected" : ""}>${item.adresse || item.email}</option>`)
    .join("");
}

function statusBadge(statut) {
  return `<span class="badge ${statut}">${statut.replaceAll("_", " ")}</span>`;
}

async function refreshAll() {
  if (!state.token) return;
  applyRoleNavigation();
  const loaders = [
    api("/dashboard").then((data) => renderDashboard(data)).catch(() => renderDashboard(null)),
    api("/logements").then((data) => { state.logements = data; renderLogements(); }).catch(() => { state.logements = []; renderLogements(); }),
    api("/reservations").then((data) => { state.reservations = data; renderReservations(); }).catch(() => { state.reservations = []; renderReservations(); }),
    api("/missions").then((data) => { state.missions = data; renderMissions(); }).catch(() => { state.missions = []; renderMissions(); }),
    api("/auth/users").then((data) => { state.users = data; renderMissions(); }).catch(() => { state.users = []; renderMissions(); }),
  ];
  await Promise.allSettled(loaders);
}

function renderDashboard(data) {
  const metrics = data || {
    logements: 0,
    reservations: 0,
    missions_a_faire: 0,
    missions_en_cours: 0,
    missions_terminees: 0,
    incidents: 0,
  };
  const labels = [
    ["Logements", metrics.logements],
    ["Reservations", metrics.reservations],
    ["A faire", metrics.missions_a_faire],
    ["En cours", metrics.missions_en_cours],
    ["Terminees", metrics.missions_terminees],
    ["Incidents", metrics.incidents],
  ];
  $("#metrics").innerHTML = labels
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderLogementSelects() {
  $$('select[name="logement_id"]').forEach((select) => {
    select.innerHTML = `<option value="">Choisir</option>${optionList(state.logements)}`;
  });
}

function renderLogements() {
  renderLogementSelects();
  $("#logementsList").innerHTML = state.logements.length
    ? state.logements.map((logement) => `
      <article class="item">
        <div class="item-head">
          <div>
            <div class="item-title">${logement.adresse}</div>
            <div class="meta">Statut: ${logement.statut}</div>
          </div>
          <button type="button" data-code="${logement.id}">Code</button>
        </div>
      </article>
    `).join("")
    : `<p class="hint">Aucun logement accessible.</p>`;
}

function renderReservations() {
  $("#reservationsList").innerHTML = state.reservations.length
    ? state.reservations.map((reservation) => {
      const logement = state.logements.find((item) => item.id === reservation.logement_id);
      return `
        <article class="item">
          <div class="item-title">${reservation.voyageur_nom}</div>
          <div class="meta">${logement?.adresse || reservation.logement_id}</div>
          <div class="meta">Arrivee: ${fmtDate(reservation.date_arrivee)} | Depart: ${fmtDate(reservation.date_depart)}</div>
          <div class="meta">Source: ${reservation.source || "manuel"} ${reservation.voyageur_contact || ""}</div>
        </article>
      `;
    }).join("")
    : `<p class="hint">Aucune reservation accessible.</p>`;
}

async function renderChecklist(mission) {
  const container = $(`[data-checklist-for="${mission.id}"]`);
  if (!container) return;
  try {
    const items = await api(`/missions/${mission.id}/checklist`);
    container.innerHTML = items.map((item) => `
      <label class="check-row">
        <input type="checkbox" ${item.coche ? "checked" : ""} data-check="${mission.id}:${item.id}">
        <span>${item.libelle}</span>
      </label>
    `).join("");
  } catch (error) {
    container.innerHTML = `<p class="hint">${error.message}</p>`;
  }
}

async function renderIncidents(mission) {
  const container = $(`[data-incidents-for="${mission.id}"]`);
  if (!container) return;
  try {
    const incidents = await api(`/missions/${mission.id}/incidents`);
    container.innerHTML = incidents.length
      ? `
        <div class="incident-list">
          <div class="section-title">Incidents signales</div>
          ${incidents.map((incident) => `
            <article class="incident">
              <div>${incident.description}</div>
              <div class="meta">${fmtDate(incident.created_at)}</div>
              ${incident.photo_url ? `<a href="${incident.photo_url}" target="_blank" rel="noreferrer">Voir la photo</a>` : ""}
            </article>
          `).join("")}
        </div>
      `
      : "";
  } catch (error) {
    container.innerHTML = `<p class="hint">${error.message}</p>`;
  }
}

function renderMissions() {
  const agents = state.users.filter((user) => user.role === "agent_menage");
  $("#missionsList").innerHTML = state.missions.length
    ? state.missions.map((mission) => {
      const logement = state.logements.find((item) => item.id === mission.logement_id);
      const agent = state.users.find((user) => user.id === mission.agent_id);
      const assignControls = canAssignMissions() ? `
        <select data-agent-for="${mission.id}">
          <option value="">Agent</option>
          ${optionList(agents, mission.agent_id)}
        </select>
        <button type="button" data-assign="${mission.id}">Assigner</button>
      ` : "";
      const statusControls = canEditChecklist() ? `
        <select data-status-for="${mission.id}">
          <option value="a_faire" ${mission.statut === "a_faire" ? "selected" : ""}>A faire</option>
          <option value="en_cours" ${mission.statut === "en_cours" ? "selected" : ""}>En cours</option>
          <option value="termine" ${mission.statut === "termine" ? "selected" : ""}>Termine</option>
          <option value="probleme_signale" ${mission.statut === "probleme_signale" ? "selected" : ""}>Probleme signale</option>
        </select>
        <button type="button" data-status="${mission.id}">Changer statut</button>
      ` : "";
      const incidentForm = canReportIncidents() ? `
        <form class="stack" data-incident-form="${mission.id}">
          <textarea name="description" placeholder="Incident ou commentaire photo" required minlength="3"></textarea>
          <input name="photo" type="file" accept="image/png,image/jpeg,image/webp">
          <button type="submit">Signaler incident</button>
        </form>
      ` : "";
      return `
        <article class="item">
          <div class="item-head">
            <div>
              <div class="item-title">${logement?.adresse || mission.logement_id}</div>
              <div class="meta">Prevue: ${fmtDate(mission.date_prevue)}</div>
              <div class="meta">Agent: ${agent?.email || mission.agent_id || "Non assigne"}</div>
            </div>
            ${statusBadge(mission.statut)}
          </div>
          <div class="actions">
            ${assignControls}
            ${statusControls}
          </div>
          <div data-checklist-for="${mission.id}" class="stack"></div>
          <div data-incidents-for="${mission.id}" class="stack"></div>
          ${incidentForm}
        </article>
      `;
    }).join("")
    : `<p class="hint">Aucune mission accessible.</p>`;
  state.missions.forEach(renderChecklist);
  state.missions.forEach(renderIncidents);
}

function setView(name) {
  if (!canUseView(name)) {
    toast("Vue non disponible pour ce role");
    return;
  }
  state.activeView = name;
  $$(".nav-btn").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
  $$(".view").forEach((view) => view.classList.add("hidden"));
  $(`#${name}View`).classList.remove("hidden");
}

function bindForms() {
  $("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const body = new URLSearchParams({ username: form.get("email"), password: form.get("password") });
    try {
      const data = await api("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      setSession(data.access_token, form.get("email"));
      await refreshAll();
      toast("Connexion reussie");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(form)),
      });
      $("#loginForm").email.value = form.get("email");
      $("[data-auth-tab='login']").click();
      toast("Compte cree, vous pouvez vous connecter");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#logementForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api("/logements", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
      formElement.reset();
      await refreshAll();
      toast("Logement ajoute");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#reservationForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const values = Object.fromEntries(new FormData(formElement));
    try {
      await api("/reservations", { method: "POST", body: JSON.stringify(values) });
      formElement.reset();
      await refreshAll();
      toast("Reservation ajoutee et mission creee");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#reservationImportForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const logementId = form.get("logement_id");
    form.delete("logement_id");
    try {
      await api(`/reservations/import?logement_id=${encodeURIComponent(logementId)}`, {
        method: "POST",
        body: form,
      });
      formElement.reset();
      await refreshAll();
      toast("Reservations importees");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#icalImportForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (!form.get("calendar_url") && !(form.get("file") instanceof File && form.get("file").size > 0)) {
      toast("Ajoute une URL iCal ou un fichier .ics");
      return;
    }
    try {
      await api("/reservations/import-ical", {
        method: "POST",
        body: form,
      });
      formElement.reset();
      await refreshAll();
      toast("Calendrier synchronise");
    } catch (error) {
      toast(error.message);
    }
  });

  $("#userForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    try {
      await api("/auth/users", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(formElement))),
      });
      formElement.reset();
      await refreshAll();
      toast("Utilisateur cree");
    } catch (error) {
      toast(error.message);
    }
  });
}

function bindClicks() {
  document.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    if (target.dataset.authTab) {
      $$(".tab").forEach((button) => button.classList.toggle("active", button === target));
      $("#loginForm").classList.toggle("hidden", target.dataset.authTab !== "login");
      $("#registerForm").classList.toggle("hidden", target.dataset.authTab !== "register");
    }

    if (target.dataset.view) setView(target.dataset.view);

    if (target.id === "logoutBtn") {
      clearSession();
      toast("Session fermee");
    }

    if (target.dataset.code) {
      try {
        const data = await api(`/logements/${target.dataset.code}/code-acces`);
        toast(`Code d'acces: ${data.code_acces || "non renseigne"}`);
      } catch (error) {
        toast(error.message);
      }
    }

    if (target.dataset.assign) {
      const missionId = target.dataset.assign;
      const agentId = $(`[data-agent-for="${missionId}"]`).value;
      try {
        await api(`/missions/${missionId}/assign`, {
          method: "PATCH",
          body: JSON.stringify({ agent_id: agentId }),
        });
        await refreshAll();
        toast("Mission assignee");
      } catch (error) {
        toast(error.message);
      }
    }

    if (target.dataset.status) {
      const missionId = target.dataset.status;
      const statut = $(`[data-status-for="${missionId}"]`).value;
      try {
        await api(`/missions/${missionId}/status`, {
          method: "PATCH",
          body: JSON.stringify({ statut }),
        });
        await refreshAll();
        toast("Statut mis a jour");
      } catch (error) {
        toast(error.message);
      }
    }
  });

  document.addEventListener("change", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement) || !target.dataset.check) return;
    const [missionId, itemId] = target.dataset.check.split(":");
    try {
      await api(`/missions/${missionId}/checklist/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ coche: target.checked }),
      });
      toast("Checklist mise a jour");
    } catch (error) {
      toast(error.message);
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.incidentForm) return;
    event.preventDefault();
    const missionId = form.dataset.incidentForm;
    const data = new FormData(form);
    const hasPhoto = data.get("photo") instanceof File && data.get("photo").size > 0;
    try {
      if (hasPhoto) {
        await api(`/missions/${missionId}/incidents/upload`, { method: "POST", body: data });
      } else {
        await api(`/missions/${missionId}/incidents`, {
          method: "POST",
          body: JSON.stringify({ description: data.get("description"), photo_url: null }),
        });
      }
      form.reset();
      await refreshAll();
      toast("Incident signale");
    } catch (error) {
      toast(error.message);
    }
  });
}

bindForms();
bindClicks();
renderSession();
setView("dashboard");
refreshAll();

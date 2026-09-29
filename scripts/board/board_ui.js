"use strict";
/* Live board UI (standards/22-live-board.md). Pure view functions plus start(), which wires
   them to a document. board.html loads it in the browser; scripts/tests/board_ui.test.js
   requires it in Node, so the same code is measured that the page runs. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.BoardView = api;
    api.start(root.document, root, root.fetch.bind(root));
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  const POLL_MS = 1500;
  const LANG_KEY = "board.lang";
  const LIVE = new Set(["starting", "running"]);
  const I18N = {
    tr: {
      title: "Canlı İş Panosu", mode: "Mod", lastEvent: "son olay:", agentsHdr: "Ajanlar",
      tasksHdr: "İşler", activityHdr: "Ajan hareketleri", colTask: "İş", colBranch: "Dal",
      colRole: "Rol / ajan", colStatus: "Durum", colTime: "Süre", colNote: "Not",
      colAgent: "Ajan", colStarted: "Başladı", turnOpen: "Claude çalışıyor", turnClosed: "Tur bitti",
      noSession: "Oturum yok", allDone: "Tüm işler bitti.", remove: "Çıkar", restore: "Geri al",
      noTasks: "Henüz iş yok — Claude plan yazınca burada görünecek.", noAgents: "Henüz ajan başlatılmadı.",
      running: "çalışan", stRunning: "Çalışıyor", stWaiting: "Bekliyor", stDone: "Bitti",
      stRemoved: "Çıkarıldı", stPlanned: "Planlandı", unreachable: "Sunucuya ulaşılamıyor",
      notMeasured: "ölçülemiyor", sec: "sn", min: "dk", hr: "sa", roleOff: "kapalı", roleOn: "açık",
      s_planned: "planlandı", s_running: "çalışıyor", s_agent_done: "ajan bitti · onay bekliyor",
      s_waiting: "bekliyor", s_done: "bitti", s_failed: "başarısız", s_removed: "çıkarıldı",
      s_starting: "başlıyor", s_denied: "reddedildi",
    },
    en: {
      title: "Live Work Board", mode: "Mode", lastEvent: "last event:", agentsHdr: "Agents",
      tasksHdr: "Tasks", activityHdr: "Agent activity", colTask: "Task", colBranch: "Branch",
      colRole: "Role / agent", colStatus: "Status", colTime: "Time", colNote: "Note",
      colAgent: "Agent", colStarted: "Started", turnOpen: "Claude is working", turnClosed: "Turn finished",
      noSession: "No session", allDone: "All tasks are done.", remove: "Remove", restore: "Restore",
      noTasks: "No tasks yet — they appear once Claude writes the plan.", noAgents: "No agent started yet.",
      running: "running", stRunning: "Running", stWaiting: "Waiting", stDone: "Done",
      stRemoved: "Removed", stPlanned: "Planned", unreachable: "Server unreachable",
      notMeasured: "not measured", sec: "s", min: "m", hr: "h", roleOff: "off", roleOn: "on",
      s_planned: "planned", s_running: "running", s_agent_done: "agent done · awaiting review",
      s_waiting: "waiting", s_done: "done", s_failed: "failed", s_removed: "removed",
      s_starting: "starting", s_denied: "denied",
    },
  };

  const makeT = (lang) => (k) => (I18N[lang] || {})[k] ?? I18N.tr[k] ?? k;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pad = (n) => String(n).padStart(2, "0");
  // #12: dd/mm/yyyy, built by hand — no locale-aware formatting.
  const fmtDate = (d) => `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
  const fmtTime = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

  function fmtStamp(iso, now = new Date()) {
    if (!iso) return "–";
    const d = new Date(iso);
    return fmtDate(d) === fmtDate(now) ? fmtTime(d) : `${fmtDate(d)} ${fmtTime(d)}`;
  }

  function fmtDur(t, fromIso, toIso, now = new Date()) {
    if (!fromIso) return t("notMeasured");
    const s = Math.max(0, Math.round(((toIso ? new Date(toIso) : now) - new Date(fromIso)) / 1000));
    if (s < 60) return `${s} ${t("sec")}`;
    if (s < 3600) return `${Math.floor(s / 60)} ${t("min")} ${s % 60} ${t("sec")}`;
    return `${Math.floor(s / 3600)} ${t("hr")} ${Math.floor(s / 60) % 60} ${t("min")}`;
  }

  const badge = (t, status) => `<span class="badge s-${esc(status)}">${esc(t("s_" + status))}</span>`;

  function taskSpan(task, agents) {
    const own = task.agents.map((k) => agents[k]).filter(Boolean);
    if (!own.length) return [null, null];
    const start = own.map((a) => a.started).sort()[0];
    const live = own.some((a) => LIVE.has(a.status));
    const end = live ? null : own.map((a) => a.ended).filter(Boolean).sort().pop();
    return [start, end];
  }

  function liveAgents(task, agents) {
    const live = task.agents.map((k) => agents[k]).filter((a) => a && LIVE.has(a.status));
    return live.length ? `<div class="live-agents">${live.map((a) =>
      `<span class="agent-chip"><span class="dot on"></span>${esc(a.type)}</span>`).join("")}</div>` : "";
  }

  /** Everything the page shows, computed from the server state; no DOM access. */
  function view(st, t, now = new Date()) {
    const tasks = Object.values(st.tasks);
    const agents = st.agents;
    const agentList = Object.values(agents).sort((a, b) => (b.started || "").localeCompare(a.started || ""));
    const sessions = Object.values(st.sessions);
    const turnOpen = sessions.some((s) => s.turn_open);
    const count = (pred) => tasks.filter(pred).length;
    const stats = [
      [t("stRunning"), count((x) => x.status === "running")],
      [t("stWaiting"), count((x) => x.status === "waiting" || x.status === "agent_done")],
      [t("stPlanned"), count((x) => x.status === "planned")],
      [t("stDone"), count((x) => x.status === "done")],
      [t("stRemoved"), count((x) => x.status === "removed")],
    ];
    const active = tasks.filter((x) => x.status !== "removed");
    const disabled = new Set(st.control.disabled_roles);
    // A role that was only ever DENIED gets no switch: it is not part of the mode.
    const started = agentList.filter((a) => a.status !== "denied").map((a) => a.type);
    const roleNames = [...new Set([...(st.roles || []), ...started, ...disabled])].filter(Boolean);
    return {
      mode: st.mode ?? "–",
      last: fmtStamp(st.last_event, now),
      turnOpen,
      turnText: !sessions.length ? t("noSession") : turnOpen ? t("turnOpen") : t("turnClosed"),
      statsHtml: stats.map(([l, n]) =>
        `<div class="stat"><div class="n">${n}</div><div class="l">${esc(l)}</div></div>`).join(""),
      allDone: active.length > 0 && active.every((x) => x.status === "done") &&
        !agentList.some((a) => LIVE.has(a.status)),
      rolesHtml: roleNames.map((r) => {
        const on = !disabled.has(r);
        const n = agentList.filter((a) => a.type === r && LIVE.has(a.status)).length;
        return `<div class="role${on ? "" : " off"}"><button class="switch" role="switch" aria-checked="${on}"
          aria-label="${esc(r)} ${esc(on ? t("roleOn") : t("roleOff"))}" data-role="${esc(r)}"></button>
          <span>${esc(r)}</span><span class="cnt">${n} ${esc(t("running"))}</span></div>`;
      }).join(""),
      tasksHtml: !tasks.length ? `<tr><td colspan="7" class="empty">${esc(t("noTasks"))}</td></tr>` :
        tasks.map((x) => {
          const [start, end] = taskSpan(x, agents);
          const removed = x.status === "removed";
          return `<tr class="${removed ? "removed" : ""}">
            <td><span class="tid">${esc(x.id)}</span><span class="title">${esc(x.title)}</span></td>
            <td>${x.branch ? `<code>${esc(x.branch)}</code>` : "—"}</td>
            <td>${esc(x.role || "—")}${liveAgents(x, agents)}</td><td>${badge(t, x.status)}</td>
            <td class="muted">${start ? esc(fmtDur(t, start, end, now)) : "—"}</td>
            <td>${esc(x.note)}</td>
            <td><button class="act" data-task="${esc(x.id)}" data-action="${removed ? "restore_task" : "remove_task"}">
              ${esc(removed ? t("restore") : t("remove"))}</button></td></tr>`;
        }).join(""),
      agentsHtml: !agentList.length ? `<tr><td colspan="6" class="empty">${esc(t("noAgents"))}</td></tr>` :
        agentList.slice(0, 30).map((a) => `<tr><td>${esc(a.type)}</td><td>${esc(a.task || "—")}</td>
          <td>${badge(t, a.status)}</td><td class="muted">${esc(fmtStamp(a.started, now))}</td>
          <td class="muted">${esc(a.status === "denied" ? "—" : fmtDur(t, a.started, a.ended, now))}</td>
          <td>${esc(a.reason || a.description)}</td></tr>`).join(""),
    };
  }

  function readLang(win) {
    try { return win.localStorage.getItem(LANG_KEY); } catch { return null; }
  }

  function writeLang(win, lang) {
    try { win.localStorage.setItem(LANG_KEY, lang); } catch { /* per-viewer convenience only */ }
  }

  /** Wires the view to a document: polling, controls, language switch. */
  function start(doc, win, fetchImpl) {
    const stored = readLang(win);
    let lang = I18N[stored] ? stored : "tr";  // tr is the primary locale
    let t = makeT(lang);
    let lastState = null;
    const $ = (id) => doc.getElementById(id);

    function applyStatic() {
      doc.documentElement.lang = lang;
      doc.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
      doc.title = t("title");
      $("lang").textContent = lang === "tr" ? "EN" : "TR";
    }

    function render(st) {
      lastState = st;
      const v = view(st, t);
      $("mode").textContent = v.mode;
      $("last").textContent = v.last;
      $("dot").className = "dot" + (v.turnOpen ? " on" : "");
      $("turn").textContent = v.turnText;
      $("stats").innerHTML = v.statsHtml;
      $("banner").classList.toggle("show", v.allDone);
      $("roles").innerHTML = v.rolesHtml;
      $("tasks").innerHTML = v.tasksHtml;
      $("agents").innerHTML = v.agentsHtml;
    }

    async function refresh() {
      try {
        const res = await fetchImpl("/api/state", { cache: "no-store" });
        render(await res.json());
        $("err").textContent = "";
      } catch (err) {
        $("err").textContent = t("unreachable");
        win.console.error("board refresh failed", err);
      }
    }

    async function control(action, value) {
      const res = await fetchImpl("/api/control", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, value }),
      });
      const refused = res.ok ? "" : (await res.json()).error;
      await refresh();  // refresh clears the error line, so a refusal is written after it
      if (refused) $("err").textContent = refused;
    }

    function onClick(e) {
      if (e.target.id === "lang") {
        lang = lang === "tr" ? "en" : "tr";
        t = makeT(lang);
        writeLang(win, lang);
        applyStatic();
        if (lastState) render(lastState);
        return null;
      }
      const sw = e.target.closest("[data-role]");
      if (sw) return control(sw.getAttribute("aria-checked") === "true" ? "disable_role" : "enable_role", sw.dataset.role);
      const btn = e.target.closest("[data-task]");
      return btn ? control(btn.dataset.action, btn.dataset.task) : null;
    }

    doc.addEventListener("click", onClick);
    applyStatic();
    const first = refresh();
    win.setInterval(refresh, POLL_MS);
    return { first, refresh, control, onClick, lang: () => lang };
  }

  return { I18N, makeT, esc, fmtDate, fmtTime, fmtStamp, fmtDur, view, start };
});

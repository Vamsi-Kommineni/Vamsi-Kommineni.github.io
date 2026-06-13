/* Vamsi Kommineni site behaviour. No dependencies. */
(function () {
  "use strict";
  var root = document.documentElement;

  /* ---------- avatar: reveal the CSS "VK" monogram if the photo can't load ---------- */
  document.querySelectorAll(".avatar img, .tb-avatar").forEach(function (img) {
    function fail() { img.style.display = "none"; }
    img.addEventListener("error", fail);
    if (img.complete && img.naturalWidth === 0) fail();   // already failed before JS ran
  });

  /* ---------- theme toggle (persisted) ---------- */
  var themeBtns = ["theme-toggle", "theme-toggle-m"]
    .map(function (id) { return document.getElementById(id); })
    .filter(Boolean);
  function setTheme(t) {
    root.dataset.theme = t;
    try { localStorage.setItem("theme", t); } catch (e) {}
    var next = t === "dark" ? "light" : "dark";
    themeBtns.forEach(function (b) {
      b.setAttribute("aria-label", "Switch to " + next + " theme");
      b.setAttribute("aria-pressed", String(t === "dark"));
    });
  }
  function toggleTheme() {
    setTheme(root.dataset.theme === "dark" ? "light" : "dark");
  }
  themeBtns.forEach(function (el) { el.addEventListener("click", toggleTheme); });
  setTheme(root.dataset.theme || "light");   // sync ARIA state with current theme

  /* ---------- mobile drawer (with focus management) ---------- */
  var sidebar = document.getElementById("sidebar");
  var scrim = document.getElementById("scrim");
  var burger = document.getElementById("burger");
  var mainEl = document.getElementById("main");
  function focusables() {
    return sidebar.querySelectorAll("a[href], button:not([disabled])");
  }
  function openNav() {
    sidebar.classList.add("open");
    scrim.hidden = false;
    requestAnimationFrame(function () { scrim.classList.add("show"); });
    burger.setAttribute("aria-expanded", "true");
    if (mainEl) mainEl.setAttribute("inert", "");   // remove background from tab order / a11y tree
    var f = focusables();
    if (f.length) f[0].focus();
  }
  function closeNav() {
    if (!sidebar.classList.contains("open")) return;
    sidebar.classList.remove("open");
    scrim.classList.remove("show");
    burger.setAttribute("aria-expanded", "false");
    if (mainEl) mainEl.removeAttribute("inert");
    setTimeout(function () { scrim.hidden = true; }, 250);
    burger.focus();
  }
  if (burger) {
    burger.addEventListener("click", function () {
      sidebar.classList.contains("open") ? closeNav() : openNav();
    });
    scrim.addEventListener("click", closeNav);
    document.addEventListener("keydown", function (e) {
      if (!sidebar.classList.contains("open")) return;
      if (e.key === "Escape") { closeNav(); return; }
      if (e.key !== "Tab") return;
      var f = Array.prototype.slice.call(focusables());
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  /* ---------- clipboard helper ---------- */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error("copy failed"));
      } catch (e) { reject(e); }
    });
  }

  /* ---------- publications: cite toggle + copy BibTeX ---------- */
  document.querySelectorAll(".cite-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wrap = document.getElementById(btn.getAttribute("aria-controls"));
      if (!wrap) return;
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!open));
      wrap.hidden = open;
    });
  });
  document.querySelectorAll(".copy-bib").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wrap = document.getElementById(btn.getAttribute("data-bib"));
      var pre = wrap && wrap.querySelector(".bibtex");
      if (!pre) return;
      var label = btn.querySelector(".copy-label");
      var prev = label ? label.textContent : "";
      function restore() {
        btn.classList.remove("copied");
        if (label) label.textContent = prev;
      }
      copyText(pre.textContent).then(function () {
        btn.classList.add("copied");
        if (label) label.textContent = "Copied!";
        setTimeout(restore, 1600);
      }).catch(function () {
        if (label) label.textContent = "Press Ctrl+C";
        setTimeout(restore, 1600);
      });
    });
  });

  /* ---------- publications: filter + search ---------- */
  var pubRoot = document.getElementById("pub-root");
  if (pubRoot) {
    var items = Array.prototype.slice.call(pubRoot.querySelectorAll(".pub"));
    var groups = Array.prototype.slice.call(pubRoot.querySelectorAll(".pubgroup-wrap"));
    var searchEl = document.getElementById("pub-search");
    var yearEl = document.getElementById("pub-year");
    var countEl = document.getElementById("pub-count");
    var noRes = document.getElementById("no-results");
    var fbtns = Array.prototype.slice.call(pubRoot.querySelectorAll(".fbtn"));
    var state = { type: "all", year: "all", q: "" };
    var total = items.length;

    function apply() {
      var shown = 0;
      items.forEach(function (li) {
        var okType = state.type === "all" || li.dataset.type === state.type;
        var okYear = state.year === "all" || li.dataset.year === state.year;
        var okQ = !state.q || li.dataset.search.indexOf(state.q) !== -1;
        var vis = okType && okYear && okQ;
        li.hidden = !vis;
        if (vis) shown++;
      });
      groups.forEach(function (g) {
        var any = g.querySelectorAll(".pub:not([hidden])").length > 0;
        g.hidden = !any;
      });
      if (noRes) noRes.hidden = shown !== 0;
      if (countEl) {
        countEl.textContent = (state.type === "all" && state.year === "all" && !state.q)
          ? total + " publications"
          : "Showing " + shown + " of " + total;
      }
    }

    var searchTimer;
    if (searchEl) searchEl.addEventListener("input", function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        state.q = searchEl.value.trim().toLowerCase(); apply();
      }, 180);   // debounce so the aria-live count isn't announced every keystroke
    });
    if (yearEl) yearEl.addEventListener("change", function () {
      state.year = yearEl.value; apply();
    });
    fbtns.forEach(function (b) {
      b.addEventListener("click", function () {
        fbtns.forEach(function (x) { x.classList.remove("active"); x.setAttribute("aria-pressed", "false"); });
        b.classList.add("active"); b.setAttribute("aria-pressed", "true");
        state.type = b.dataset.filter; apply();
      });
    });
    var clearBtn = document.getElementById("clear-filters");
    if (clearBtn) clearBtn.addEventListener("click", function () {
      state = { type: "all", year: "all", q: "" };
      if (searchEl) searchEl.value = "";
      if (yearEl) yearEl.value = "all";
      fbtns.forEach(function (x) {
        var on = x.dataset.filter === "all";
        x.classList.toggle("active", on); x.setAttribute("aria-pressed", String(on));
      });
      apply();
    });

    apply();
  }
})();

/* Progressive enhancement only: every page works without this file. */
(function () {
  "use strict";

  // 1. Assemble the email address so it is not sitting in the HTML as plain text.
  document.querySelectorAll(".email[data-user]").forEach(function (el) {
    var addr = el.dataset.user + "@" + el.dataset.domain;
    var a = document.createElement("a");
    a.href = "mailto:" + addr;
    a.textContent = addr;
    el.replaceWith(a);
  });

  // 2. Project filter (home page).
  var filters = document.querySelectorAll(".filter");
  var cards = document.querySelectorAll("#cards .card");
  var status = document.getElementById("filter-status");
  filters.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var f = btn.dataset.filter;
      var shown = 0;
      filters.forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      cards.forEach(function (c) {
        var match = f === "all" || c.dataset.cats.split(" ").indexOf(f) !== -1;
        c.hidden = !match;
        if (match) shown += 1;
      });
      // The first visible card becomes the wide feature card.
      var first = true;
      cards.forEach(function (c) {
        if (c.hidden) return;
        c.classList.toggle("feature", first && f === "all");
        first = false;
      });
      if (status) status.textContent = "Showing " + shown + " of " + cards.length + " projects";
    });
  });

  // 3. Hero inspection sheet: switch between the two scan states.
  var sheet = document.querySelector("[data-sheet]");
  if (sheet) {
    var states = sheet.querySelectorAll(".state");
    var rows = sheet.querySelectorAll(".titleblock tr");
    var tabs = document.createElement("div");
    tabs.className = "sheet-tabs";
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", "Inspection scan state");
    var buttons = [];
    var select = function (i) {
      states.forEach(function (s, j) { s.classList.toggle("is-active", i === j); });
      buttons.forEach(function (b, j) {
        b.setAttribute("aria-selected", i === j ? "true" : "false");
        b.tabIndex = i === j ? 0 : -1;
      });
      var tag = states[i].dataset.tag;
      rows.forEach(function (r) {
        r.classList.toggle("is-current", r.firstElementChild.textContent.trim() === tag);
      });
    };
    states.forEach(function (s, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.textContent = s.dataset.tag;
      b.addEventListener("click", function () { select(i); });
      b.addEventListener("keydown", function (e) {
        var n = null;
        if (e.key === "ArrowRight") n = (i + 1) % states.length;
        if (e.key === "ArrowLeft") n = (i - 1 + states.length) % states.length;
        if (n !== null) { select(n); buttons[n].focus(); e.preventDefault(); }
      });
      buttons.push(b);
      tabs.appendChild(b);
    });
    sheet.classList.add("js");
    sheet.insertBefore(tabs, sheet.firstChild);
    select(0);
  }

  // 4. Lightbox for technical images. Links still open the file directly without JS.
  var box = document.getElementById("lightbox");
  if (box && typeof box.showModal === "function") {
    var big = box.querySelector("img");
    var cap = box.querySelector("figcaption");
    var last = null;
    document.addEventListener("click", function (e) {
      var a = e.target.closest("a.zoom");
      if (!a) return;
      e.preventDefault();
      last = a;
      big.removeAttribute("style");
      big.onload = function () { big.style.setProperty("--lb-w", big.naturalWidth + "px"); };
      big.src = a.href;
      big.alt = a.dataset.alt || "";
      cap.textContent = a.dataset.caption || "";
      box.showModal();
      box.querySelector(".lb-close").focus();
    });
    box.querySelector(".lb-close").addEventListener("click", function () { box.close(); });
    box.addEventListener("click", function (e) { if (e.target === box) box.close(); });
    box.addEventListener("close", function () { if (last) last.focus(); });
  }
})();

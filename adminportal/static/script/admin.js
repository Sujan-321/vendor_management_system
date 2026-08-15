(function () {
  "use strict";

  /* Sidebar toggle (mobile drawer + desktop collapse) */
  var shell = document.querySelector(".app-shell");
  var toggleBtns = document.querySelectorAll("[data-sidebar-toggle]");
  toggleBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      shell.classList.toggle("is-collapsed");
    });
  });

  document.addEventListener("click", function (e) {
    if (window.innerWidth > 900) return;
    if (!shell.classList.contains("is-collapsed")) return;
    if (e.target.closest(".sidebar") || e.target.closest("[data-sidebar-toggle]")) return;
    shell.classList.remove("is-collapsed");
  });

  /* Dismissible alerts */
  document.querySelectorAll(".alert-close").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var alert = btn.closest(".alert");
      if (!alert) return;
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 150);
    });
  });

  /* Auto-dismiss success alerts after 6s */
  document.querySelectorAll(".alert-success, .alert-info").forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity .3s ease";
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 300);
    }, 6000);
  });

  /* Dropdown menus (profile, row actions) */
  document.querySelectorAll("[data-dropdown-toggle]").forEach(function (btn) {
    var menu = document.getElementById(btn.getAttribute("data-dropdown-toggle"));
    if (!menu) return;
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      document.querySelectorAll(".dropdown-menu.is-open").forEach(function (m) {
        if (m !== menu) m.classList.remove("is-open");
      });
      menu.classList.toggle("is-open");
    });
  });
  document.addEventListener("click", function () {
    document.querySelectorAll(".dropdown-menu.is-open").forEach(function (m) {
      m.classList.remove("is-open");
    });
  });

  /* Confirm-delete modal: any element with data-confirm-modal="modalId" opens that <dialog> */
  document.querySelectorAll("[data-confirm-modal]").forEach(function (trigger) {
    trigger.addEventListener("click", function (e) {
      var dialogId = trigger.getAttribute("data-confirm-modal");
      var dialog = document.getElementById(dialogId);
      if (!dialog) return;
      e.preventDefault();
      dialog.showModal();
    });
  });
  document.querySelectorAll("[data-modal-cancel]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var dialog = btn.closest("dialog");
      if (dialog) dialog.close();
    });
  });

  /* Simple client-side table search: input[data-table-search] filters rows in the named table */
  document.querySelectorAll("[data-table-search]").forEach(function (input) {
    var table = document.querySelector(input.getAttribute("data-table-search"));
    if (!table) return;
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (row) {
        row.style.display = row.innerText.toLowerCase().indexOf(q) > -1 ? "" : "none";
      });
    });
  });
})();
/* Small, dependency-free behavior shared by all pages. */
(() => {
  "use strict";
  const sidebar = document.querySelector("[data-sidebar]");
  const backdrop = document.querySelector("[data-sidebar-overlay]");

  function setSidebarOpen(open) {
    document.body.classList.toggle("sidebar-open", open);
    if (backdrop) backdrop.hidden = !open;
    const opener = document.querySelector("[data-sidebar-open]");
    if (opener) opener.setAttribute("aria-expanded", String(open));
    if (!open && opener && window.matchMedia("(max-width: 900px)").matches) opener.focus();
  }

  document.querySelectorAll("[data-sidebar-open]").forEach((button) => {
    button.addEventListener("click", () => setSidebarOpen(true));
  });
  document.querySelectorAll("[data-sidebar-close], [data-sidebar-overlay]").forEach((element) => {
    element.addEventListener("click", () => setSidebarOpen(false));
  });
  if (sidebar) {
    sidebar.querySelectorAll("a.nav-child").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 900px)").matches) setSidebarOpen(false);
      });
    });
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setSidebarOpen(false);
  });
  window.addEventListener("resize", () => {
    if (!window.matchMedia("(max-width: 900px)").matches) setSidebarOpen(false);
  });

  document.querySelectorAll("[data-modal-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = document.querySelector(button.dataset.modalOpen);
      if (!dialog) return;
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    });
  });

  document.querySelectorAll("[data-modal]").forEach((dialog) => {
    dialog.querySelectorAll("[data-modal-close]").forEach((button) => {
      button.addEventListener("click", () => {
        if (typeof dialog.close === "function") dialog.close();
        else dialog.removeAttribute("open");
      });
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog && typeof dialog.close === "function") dialog.close();
    });
    const form = dialog.querySelector("form");
    if (form) {
      form.addEventListener("submit", (event) => {
        let firstInvalid = null;
        form.querySelectorAll("[data-searchable-select][data-select-required='true']").forEach((wrapper) => {
          const value = wrapper.querySelector("[data-select-value]");
          const trigger = wrapper.querySelector("[data-select-trigger]");
          const error = wrapper.querySelector("[data-select-error]");
          const invalid = !value || !value.value;
          wrapper.classList.toggle("has-error", invalid);
          if (error) error.hidden = !invalid;
          if (invalid && !firstInvalid) firstInvalid = trigger;
        });
        if (firstInvalid) {
          event.preventDefault();
          firstInvalid.focus();
        }
      });
    }
  });

  document.querySelectorAll("[data-auto-open='true']").forEach((dialog) => {
    if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
    else dialog.setAttribute("open", "");
  });

  document.querySelectorAll("[data-dismiss-flash]").forEach((button) => {
    button.addEventListener("click", () => {
      const flash = button.closest(".flash");
      if (flash) {
        flash.classList.add("is-hiding");
        window.setTimeout(() => flash.remove(), 170);
      }
    });
  });
  document.querySelectorAll(".flash").forEach((flash) => {
    window.setTimeout(() => {
      if (!flash.isConnected) return;
      flash.classList.add("is-hiding");
      window.setTimeout(() => flash.remove(), 170);
    }, 7000);
  });

  // History back-button trapping & Exit Modal logic (Image 4)
  const isDashboardPage = window.location.pathname === "/" || window.location.pathname.startsWith("/dashboard");
  if (isDashboardPage) {
    try {
      window.history.pushState({ page: "dashboard_entry" }, "", window.location.href);
      window.addEventListener("popstate", function () {
        const exitModal = document.getElementById("exitConfirmationModal");
        if (exitModal) {
          exitModal.showModal();
          window.history.pushState({ page: "dashboard_entry" }, "", window.location.href);
        }
      });
    } catch (_) {}
  }
})();

// Global functions for exit confirmation modal
function showExitModal() {
  const modal = document.getElementById("exitConfirmationModal");
  if (modal) {
    if (typeof modal.showModal === "function") modal.showModal();
    else modal.setAttribute("open", "");
  }
}

function closeExitModal() {
  const modal = document.getElementById("exitConfirmationModal");
  if (modal) {
    if (typeof modal.close === "function") modal.close();
    else modal.removeAttribute("open");
  }
}

function handleAppBack() {
  const isDashboardPage = window.location.pathname === "/" || window.location.pathname.startsWith("/dashboard");
  if (isDashboardPage) {
    showExitModal();
  } else {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = "/dashboard";
    }
  }
}

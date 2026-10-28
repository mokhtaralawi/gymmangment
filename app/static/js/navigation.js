/* Persistent ERP tree navigation, with automatic expansion for the active route. */
(() => {
  "use strict";
  const groups = Array.from(document.querySelectorAll("[data-nav-group]"));
  if (!groups.length) return;
  const storageKey = "nadi.sidebar.open-groups.v1";
  let stored = [];
  try {
    const decoded = JSON.parse(window.localStorage.getItem(storageKey) || "[]");
    if (Array.isArray(decoded)) stored = decoded.filter((value) => typeof value === "string");
  } catch (_error) {
    stored = [];
  }

  function setOpen(group, open) {
    const button = group.querySelector("[data-nav-toggle]");
    const children = group.querySelector("[data-nav-children]");
    group.classList.toggle("is-open", open);
    if (button) button.setAttribute("aria-expanded", String(open));
    if (children) children.hidden = !open;
  }

  function persist() {
    const openGroups = groups
      .filter((group) => group.classList.contains("is-open"))
      .map((group) => group.dataset.navGroup);
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(openGroups));
    } catch (_error) {
      // Navigation should keep working even if storage is disabled.
    }
  }

  groups.forEach((group) => {
    const hasActiveRoute = group.dataset.active === "true"
      || Boolean(group.querySelector(".nav-child.is-active"));
    setOpen(group, hasActiveRoute || stored.includes(group.dataset.navGroup));
    const button = group.querySelector("[data-nav-toggle]");
    if (button) {
      button.addEventListener("click", () => {
        setOpen(group, !group.classList.contains("is-open"));
        persist();
      });
    }
  });
  persist();
})();

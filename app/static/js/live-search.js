/* Debounced server-backed search and list filters/sorting. */
(() => {
  "use strict";
  const searchForms = document.querySelectorAll("[data-live-fetch-form]");

  function applyListControls(scope = document) {
    scope.querySelectorAll("[data-results-list]").forEach((list) => {
      const controller = list.closest("[data-list-controller]") || scope;
      const activeStatus = controller.querySelector("[data-user-status-filter].is-selected")?.dataset.userStatusFilter || "all";
      const queryInput = controller.querySelector("[data-client-filter-input]");
      const query = (queryInput?.value || "").trim().toLocaleLowerCase();
      const items = Array.from(list.querySelectorAll("[data-search-item]"));
      let visibleCount = 0;
      items.forEach((item) => {
        const searchText = (item.dataset.searchText || item.textContent).toLocaleLowerCase();
        const statusMatches = activeStatus === "all" || item.dataset.status === activeStatus;
        const textMatches = !query || searchText.includes(query);
        const visible = statusMatches && textMatches;
        item.hidden = !visible;
        if (visible) visibleCount += 1;
      });
      const emptyState = controller.querySelector("[data-live-empty]");
      if (emptyState) emptyState.hidden = visibleCount > 0;
    });
  }

  searchForms.forEach((form) => {
    const input = form.querySelector("[data-live-fetch-search]");
    const target = document.querySelector(form.dataset.liveTarget || "");
    if (!input || !target || !form.dataset.liveFetch) return;
    let timer = null;
    let controller = null;

    async function runSearch() {
      if (controller) controller.abort();
      controller = new AbortController();
      const url = new URL(form.dataset.liveFetch, window.location.origin);
      const query = input.value.trim();
      if (query) url.searchParams.set("q", query);

      target.setAttribute("aria-busy", "true");
      try {
        const response = await fetch(url, {
          signal: controller.signal,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        if (response.redirected && response.url.includes("/auth/login")) {
          window.location.href = response.url;
          return;
        }
        if (!response.ok) throw new Error("تعذر تحديث نتائج البحث.");
        target.innerHTML = await response.text();
        const pagination = document.querySelector("[data-search-pagination]");
        if (pagination) pagination.hidden = Boolean(query);
        applyListControls(target.closest("[data-list-controller]") || document);
      } catch (error) {
        if (error.name !== "AbortError") {
          const notice = document.querySelector("[data-search-error]");
          if (notice) notice.hidden = false;
        }
      } finally {
        target.removeAttribute("aria-busy");
      }
    }

    input.addEventListener("input", () => {
      const notice = document.querySelector("[data-search-error]");
      if (notice) notice.hidden = true;
      window.clearTimeout(timer);
      timer = window.setTimeout(runSearch, 260);
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      window.clearTimeout(timer);
      runSearch();
    });
  });

  document.querySelectorAll("[data-user-status-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.closest(".segmented-control");
      group?.querySelectorAll("[data-user-status-filter]").forEach((candidate) => {
        const selected = candidate === button;
        candidate.classList.toggle("is-selected", selected);
        candidate.setAttribute("aria-pressed", String(selected));
      });
      applyListControls(button.closest("[data-list-controller]") || document);
    });
  });

  document.querySelectorAll("[data-sort-cycle]").forEach((button) => {
    const target = document.querySelector(button.dataset.sortTarget || "");
    if (!target) return;
    const values = (button.dataset.sortValues || "created").split(",");
    const labels = (button.dataset.sortLabels || "").split(",");
    button.addEventListener("click", () => {
      const current = Number(button.dataset.sortCurrent || 0);
      const next = (current + 1) % values.length;
      button.dataset.sortCurrent = String(next);
      const label = button.querySelector("span");
      if (label) label.textContent = "الترتيب: " + (labels[next] || values[next]);

      const items = Array.from(target.querySelectorAll("[data-search-item]"));
      const key = values[next];
      items.sort((a, b) => {
        if (key === "created") {
          return (Date.parse(b.dataset.sortCreated || "") || 0) - (Date.parse(a.dataset.sortCreated || "") || 0);
        }
        const attr = key === "name" ? "sortName" : "sortUsername";
        return (a.dataset[attr] || "").localeCompare(b.dataset[attr] || "", "ar");
      });
      items.forEach((item) => target.appendChild(item));
      applyListControls(button.closest("[data-list-controller]") || document);
    });
  });

  document.querySelectorAll("[data-results-list]").forEach((list) => {
    applyListControls(list.closest("[data-list-controller]") || document);
  });
})();

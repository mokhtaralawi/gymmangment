/* Remote searchable selects. The submitted value is always a server-validated database ID. */
(() => {
  "use strict";

  const wrappers = Array.from(document.querySelectorAll("[data-remote-select]"));
  if (!wrappers.length) return;

  const activeControllers = new WeakMap();

  function resultPanel(wrapper, visible) {
    const panel = wrapper.querySelector("[data-remote-results]");
    const input = wrapper.querySelector("[data-remote-input]");
    if (panel) panel.hidden = !visible;
    if (input) input.setAttribute("aria-expanded", String(visible));
  }

  function setError(wrapper, invalid) {
    wrapper.classList.toggle("has-error", invalid);
    const error = wrapper.querySelector("[data-remote-error]");
    if (error) error.hidden = !invalid;
  }

  function clearSelection(wrapper, { clearInput = true } = {}) {
    const value = wrapper.querySelector("[data-remote-value]");
    const input = wrapper.querySelector("[data-remote-input]");
    const meta = wrapper.querySelector("[data-remote-selected-meta]");
    if (value) {
      value.value = "";
      value.dispatchEvent(new Event("change", { bubbles: true }));
    }
    if (input && clearInput) input.value = "";
    if (meta) {
      meta.textContent = "";
      meta.hidden = true;
    }
    setError(wrapper, false);
    resultPanel(wrapper, false);
  }

  async function search(wrapper, query) {
    const urlValue = wrapper.dataset.remoteUrl;
    const input = wrapper.querySelector("[data-remote-input]");
    const status = wrapper.querySelector("[data-remote-status]");
    const options = wrapper.querySelector("[data-remote-options]");
    const dependencyName = wrapper.dataset.remoteDependsOn;
    const dependency = dependencyName
      ? wrapper.closest("form")?.querySelector('[name="' + CSS.escape(dependencyName) + '"]')
      : null;

    if (dependency && !dependency.value) {
      if (status) status.textContent = "اختر العنصر السابق أولًا.";
      if (options) options.replaceChildren();
      resultPanel(wrapper, true);
      return;
    }

    if (!query || query.length < 1) {
      if (status) status.textContent = "اكتب كلمة للبحث.";
      if (options) options.replaceChildren();
      resultPanel(wrapper, true);
      return;
    }

    const previous = activeControllers.get(wrapper);
    if (previous) previous.abort();
    const controller = new AbortController();
    activeControllers.set(wrapper, controller);
    if (status) status.textContent = "جارٍ البحث...";
    if (options) options.replaceChildren();
    resultPanel(wrapper, true);

    const url = new URL(urlValue, window.location.origin);
    url.searchParams.set("q", query);
    if (dependencyName && dependency) url.searchParams.set(dependencyName, dependency.value);

    try {
      const response = await fetch(url, {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "application/json" },
        signal: controller.signal,
      });
      if (response.redirected && response.url.includes("/auth/login")) {
        window.location.href = response.url;
        return;
      }
      if (!response.ok) throw new Error("تعذر البحث عن العناصر.");
      const payload = await response.json();
      const items = Array.isArray(payload.items) ? payload.items : [];
      if (options) {
        items.forEach((item) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "remote-select-option";
          button.setAttribute("role", "option");
          button.dataset.optionId = String(item.id);
          button.dataset.optionLabel = item.label || "";
          button.dataset.optionMeta = item.description || "";
          const label = document.createElement("span");
          label.className = "remote-option-label";
          label.textContent = item.label || "";
          button.appendChild(label);
          if (item.description) {
            const meta = document.createElement("small");
            meta.className = "remote-option-meta";
            meta.textContent = item.description;
            button.appendChild(meta);
          }
          button.addEventListener("click", () => {
            const hidden = wrapper.querySelector("[data-remote-value]");
            const textInput = wrapper.querySelector("[data-remote-input]");
            const selectedMeta = wrapper.querySelector("[data-remote-selected-meta]");
            if (hidden) {
              hidden.value = button.dataset.optionId;
              hidden.dispatchEvent(new Event("change", { bubbles: true }));
            }
            if (textInput) textInput.value = button.dataset.optionLabel;
            if (selectedMeta) {
              selectedMeta.textContent = button.dataset.optionMeta;
              selectedMeta.hidden = !button.dataset.optionMeta;
            }
            setError(wrapper, false);
            resultPanel(wrapper, false);
            wrapper.dispatchEvent(new CustomEvent("remote-select:change", {
              bubbles: true,
              detail: { id: button.dataset.optionId, item },
            }));
          });
          options.appendChild(button);
        });
      }
      if (status) {
        status.textContent = items.length ? "اختر نتيجة من القائمة." : "لا توجد نتائج مطابقة.";
        status.hidden = Boolean(items.length);
      }
    } catch (error) {
      if (error.name !== "AbortError" && status) {
        status.textContent = "تعذر البحث. تحقق من الاتصال وحاول مرة أخرى.";
        status.hidden = false;
      }
    } finally {
      if (input) input.removeAttribute("aria-busy");
    }
  }

  wrappers.forEach((wrapper) => {
    const input = wrapper.querySelector("[data-remote-input]");
    const hidden = wrapper.querySelector("[data-remote-value]");
    const dependencyName = wrapper.dataset.remoteDependsOn;
    let timer = null;
    if (!input || !hidden) return;

    input.addEventListener("input", () => {
      // Typed text is not a valid selected database reference until a result is chosen.
      if (hidden.value) clearSelection(wrapper, { clearInput: false });
      setError(wrapper, false);
      window.clearTimeout(timer);
      input.setAttribute("aria-busy", "true");
      timer = window.setTimeout(() => search(wrapper, input.value.trim()), 220);
    });
    input.addEventListener("focus", () => {
      if (input.value.trim().length >= 1 && !hidden.value) search(wrapper, input.value.trim());
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") resultPanel(wrapper, false);
      if (event.key === "ArrowDown") {
        const first = wrapper.querySelector(".remote-select-option");
        if (first) {
          event.preventDefault();
          first.focus();
        }
      }
    });
    wrapper.addEventListener("click", (event) => {
      if (!event.target.closest(".remote-select-option") && !event.target.closest("[data-remote-input]")) {
        // Outside-click handling is attached below at document level.
      }
    });

    if (dependencyName) {
      const parent = wrapper.closest("form")?.querySelector('[name="' + CSS.escape(dependencyName) + '"]');
      if (parent) {
        parent.addEventListener("change", () => {
          clearSelection(wrapper);
          input.placeholder = "اختر العنصر السابق أولًا ثم ابحث...";
        });
      }
    }
  });

  document.addEventListener("click", (event) => {
    wrappers.forEach((wrapper) => {
      if (!wrapper.contains(event.target)) resultPanel(wrapper, false);
    });
  });

  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const required = Array.from(form.querySelectorAll("[data-remote-select][data-remote-required='true']"));
      const invalid = required.find((wrapper) => {
        const value = wrapper.querySelector("[data-remote-value]");
        const bad = !value || !value.value;
        setError(wrapper, bad);
        return bad;
      });
      if (invalid) {
        event.preventDefault();
        invalid.querySelector("[data-remote-input]")?.focus();
      }
    });
  });
})();

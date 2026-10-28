/* Accessible, keyboard-friendly searchable dropdowns with no external dependency. */
(() => {
  "use strict";
  const components = Array.from(document.querySelectorAll("[data-searchable-select]"));
  if (!components.length) return;

  function close(wrapper) {
    const popover = wrapper.querySelector("[data-select-popover]");
    const trigger = wrapper.querySelector("[data-select-trigger]");
    if (popover) popover.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  }

  function closeAll(except) {
    components.forEach((wrapper) => {
      if (wrapper !== except) close(wrapper);
    });
  }

  components.forEach((wrapper) => {
    const trigger = wrapper.querySelector("[data-select-trigger]");
    const valueInput = wrapper.querySelector("[data-select-value]");
    const selectedLabel = wrapper.querySelector("[data-select-label]");
    const popover = wrapper.querySelector("[data-select-popover]");
    const searchInput = wrapper.querySelector("[data-select-search]");
    const emptyState = wrapper.querySelector("[data-select-empty]");
    const options = Array.from(wrapper.querySelectorAll("[data-option-value]"));
    const error = wrapper.querySelector("[data-select-error]");
    const placeholder = wrapper.dataset.selectPlaceholder || "اختر عنصرًا";

    function filterOptions() {
      const query = (searchInput ? searchInput.value : "").trim().toLocaleLowerCase();
      let visibleCount = 0;
      options.forEach((option) => {
        const haystack = ((option.dataset.optionSearch || "") + " "
          + (option.dataset.optionLabel || option.textContent)).toLocaleLowerCase();
        const visible = !query || haystack.includes(query);
        const item = option.closest("li");
        if (item) item.hidden = !visible;
        if (visible) visibleCount += 1;
      });
      if (emptyState) emptyState.hidden = visibleCount > 0;
    }

    function choose(option) {
      valueInput.value = option.dataset.optionValue || "";
      selectedLabel.textContent = option.dataset.optionLabel || option.textContent.trim();
      trigger.classList.remove("is-placeholder");
      options.forEach((candidate) => {
        candidate.setAttribute("aria-selected", String(candidate === option));
      });
      wrapper.classList.remove("has-error");
      if (error) error.hidden = true;
      valueInput.dispatchEvent(new Event("change", { bubbles: true }));
      close(wrapper);
      trigger.focus();
    }

    trigger.classList.toggle("is-placeholder", !valueInput.value);
    trigger.addEventListener("click", () => {
      const shouldOpen = popover.hidden;
      closeAll(wrapper);
      popover.hidden = !shouldOpen;
      trigger.setAttribute("aria-expanded", String(shouldOpen));
      if (shouldOpen) {
        searchInput.value = "";
        filterOptions();
        window.setTimeout(() => searchInput.focus(), 0);
      }
    });

    options.forEach((option) => option.addEventListener("click", () => choose(option)));
    if (searchInput) searchInput.addEventListener("input", filterOptions);
    wrapper.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && popover && !popover.hidden) {
        close(wrapper);
        trigger.focus();
      }
      if (event.key === "ArrowDown" && event.target === trigger) {
        event.preventDefault();
        popover.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        if (searchInput) searchInput.focus();
      }
    });

    if (valueInput.value) {
      const selected = options.find((option) => option.dataset.optionValue === valueInput.value);
      if (selected) choose(selected);
    } else {
      selectedLabel.textContent = placeholder;
      trigger.classList.add("is-placeholder");
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-searchable-select]")) closeAll(null);
  });
})();

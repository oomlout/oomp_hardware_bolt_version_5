document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("explore-search");
  const rows = Array.from(document.querySelectorAll(".part-card"));
  const emptyState = document.getElementById("explore-empty");
  const countNode = document.getElementById("visible-count");
  const searchFieldInputs = Array.from(document.querySelectorAll(".search-field-chip__input"));
  const taxonomyToggle = document.getElementById("taxonomy-toggle");
  const taxonomyPanel = document.getElementById("taxonomy-panel-body");
  const taxonomyStorageKey = "partsExplorer.taxonomyCollapsed";

  if (taxonomyToggle && taxonomyPanel) {
    const collapseTaxonomy = (collapsed) => {
      taxonomyToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      taxonomyPanel.classList.toggle("is-collapsed", collapsed);
      const stateNode = taxonomyToggle.querySelector(".taxonomy-toggle__state");
      if (stateNode) {
        stateNode.textContent = collapsed ? "Collapsed" : "Open";
      }
      window.localStorage.setItem(taxonomyStorageKey, collapsed ? "true" : "false");
    };

    const storedValue = window.localStorage.getItem(taxonomyStorageKey);
    if (storedValue === "true") {
      collapseTaxonomy(true);
    }

    taxonomyToggle.addEventListener("click", () => {
      const expanded = taxonomyToggle.getAttribute("aria-expanded") === "true";
      collapseTaxonomy(expanded);
    });
  }

  if (!searchInput || !rows.length || !emptyState) {
    return;
  }

  const normalizeSearchText = (value) =>
    String(value || "")
      .toLowerCase()
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  const queryTokens = (value) => {
    const normalized = normalizeSearchText(value);
    return normalized === "" ? [] : normalized.split(" ").filter(Boolean);
  };

  const selectedFields = () => {
    const checked = searchFieldInputs
      .filter((input) => input.checked)
      .map((input) => input.value);
    if (checked.length > 0) {
      return checked;
    }
    return searchFieldInputs
      .filter((input) => input.dataset.defaultChecked === "true")
      .map((input) => input.value);
  };

  const applyFilter = () => {
    const tokens = queryTokens(searchInput.value);
    const activeFields = selectedFields();
    let visibleTotal = 0;

    rows.forEach((row) => {
      const searchText = normalizeSearchText(
        activeFields
        .map((fieldName) => row.getAttribute(`data-search-${fieldName.replace(/_/g, "-")}`) || "")
        .join(" "),
      );
      const matches = tokens.length === 0 || tokens.every((token) => searchText.includes(token));
      row.classList.toggle("is-hidden", !matches);
      if (matches) {
        visibleTotal += 1;
      }
    });

    emptyState.classList.toggle("is-hidden", visibleTotal > 0);
    if (countNode) {
      countNode.textContent = String(visibleTotal);
    }
  };

  searchInput.addEventListener("input", applyFilter);
  searchFieldInputs.forEach((input) => input.addEventListener("change", applyFilter));
  applyFilter();
});

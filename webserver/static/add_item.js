document.addEventListener("DOMContentLoaded", () => {
  const familySelect = document.getElementById("family-select");
  if (!familySelect) {
    return;
  }

  familySelect.addEventListener("change", () => {
    familySelect.form.submit();
  });
});

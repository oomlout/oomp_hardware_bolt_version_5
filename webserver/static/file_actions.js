document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  const message = form.dataset.confirmMessage;
  if (!message) {
    return;
  }

  if (!window.confirm(message)) {
    event.preventDefault();
  }
});
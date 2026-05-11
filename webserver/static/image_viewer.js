document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.getElementById("image-viewer");
  if (!dialog) {
    return;
  }

  const payload = { parts: {} };

  const imageNode = document.getElementById("image-viewer-image");
  const stageNode = dialog.querySelector(".image-viewer__stage");
  const codeBlockNode = document.getElementById("image-viewer-code-block");
  const codeNode = document.getElementById("image-viewer-code");
  const titleNode = document.getElementById("image-viewer-title");
  const pathNode = document.getElementById("image-viewer-path");
  const countNode = document.getElementById("image-viewer-count");
  const languageNode = document.getElementById("image-viewer-language");
  const stateNode = document.getElementById("image-viewer-state");
  const previousButton = document.getElementById("image-viewer-prev");
  const nextButton = document.getElementById("image-viewer-next");
  const closeButton = document.getElementById("image-viewer-close");
  const originalLink = document.getElementById("image-viewer-original");

  if (!imageNode || !stageNode || !codeBlockNode || !codeNode || !titleNode || !pathNode || !countNode || !languageNode || !stateNode || !previousButton || !nextButton || !closeButton || !originalLink) {
    return;
  }

  let activePartId = "";
  let activeIndex = 0;
  let activeTrigger = null;

  const resetImageSizing = () => {
    imageNode.style.width = "";
    imageNode.style.height = "";
  };

  const fitImageToStage = () => {
    if (imageNode.classList.contains("is-hidden") || !imageNode.naturalWidth || !imageNode.naturalHeight) {
      return;
    }

    const stageWidth = stageNode.clientWidth;
    const stageHeight = stageNode.clientHeight;
    if (!stageWidth || !stageHeight) {
      return;
    }

    const imageAspectRatio = imageNode.naturalWidth / imageNode.naturalHeight;
    const stageAspectRatio = stageWidth / stageHeight;

    if (imageAspectRatio >= stageAspectRatio) {
      imageNode.style.width = "100%";
      imageNode.style.height = "auto";
      return;
    }

    imageNode.style.width = "auto";
    imageNode.style.height = "100%";
  };

  const queueImageFit = () => {
    requestAnimationFrame(() => {
      fitImageToStage();
    });
  };

  const getActivePart = () => payload.parts[activePartId] || null;
  const rememberPart = (part) => {
    if (!part || !part.partId) {
      return;
    }
    payload.parts[part.partId] = part;
  };

  const preloadNeighbors = () => {
    const part = getActivePart();
    if (!part || !Array.isArray(part.items) || part.items.length < 2) {
      return;
    }
    const previous = part.items[(activeIndex - 1 + part.items.length) % part.items.length];
    const next = part.items[(activeIndex + 1) % part.items.length];
    [previous, next].forEach((item) => {
      if (item.kind !== "image") {
        return;
      }
      const preloader = new Image();
      preloader.src = item.modalUrl;
    });
  };

  const render = () => {
    const part = getActivePart();
    if (!part || !Array.isArray(part.items) || part.items.length === 0) {
      dialog.close();
      return;
    }

    if (activeIndex < 0) {
      activeIndex = part.items.length - 1;
    }
    if (activeIndex >= part.items.length) {
      activeIndex = 0;
    }

    const item = part.items[activeIndex];
    titleNode.textContent = part.partName;
    pathNode.textContent = item.relativePath;
    countNode.textContent = `${activeIndex + 1} of ${part.items.length}`;
    originalLink.href = item.originalUrl;

    if (item.kind === "image") {
      resetImageSizing();
      imageNode.src = item.modalUrl;
      imageNode.alt = `${part.partName} - ${item.relativePath}`;
      imageNode.classList.remove("is-hidden");
      codeBlockNode.classList.add("is-hidden");
      languageNode.classList.add("is-hidden");
      stateNode.classList.add("is-hidden");
      if (item.width && item.height) {
        imageNode.width = item.width;
        imageNode.height = item.height;
      } else {
        imageNode.removeAttribute("width");
        imageNode.removeAttribute("height");
      }
      queueImageFit();
    } else {
      imageNode.classList.add("is-hidden");
      imageNode.removeAttribute("src");
      imageNode.removeAttribute("width");
      imageNode.removeAttribute("height");
      resetImageSizing();
      codeBlockNode.classList.remove("is-hidden");
      codeNode.textContent = item.content || "";
      languageNode.textContent = item.languageLabel || "Text";
      languageNode.classList.remove("is-hidden");
      stateNode.textContent = item.truncated ? "Preview truncated" : "Full file";
      stateNode.classList.remove("is-hidden");
    }

    const multipleItems = part.items.length > 1;
    previousButton.disabled = !multipleItems;
    nextButton.disabled = !multipleItems;

    preloadNeighbors();
  };

  const openViewer = (partId, index, trigger) => {
    const part = payload.parts[partId];
    if (!part || !Array.isArray(part.items) || part.items.length === 0) {
      return;
    }
    activePartId = partId;
    activeIndex = Number.isFinite(index) ? index : 0;
    activeTrigger = trigger || null;
    render();
    if (!dialog.open) {
      dialog.showModal();
    }
    queueImageFit();
    closeButton.focus();
  };

  imageNode.addEventListener("load", () => {
    queueImageFit();
  });

  const fetchPartPayload = async (trigger, partId) => {
    const requestUrl = trigger.getAttribute("data-image-viewer-url") || "";
    if (!requestUrl) {
      return null;
    }
    const response = await fetch(requestUrl, {
      headers: {
        Accept: "application/json",
      },
    });
    if (!response.ok) {
      return null;
    }
    const part = await response.json();
    rememberPart(part);
    return part;
  };

  document.querySelectorAll("[data-image-viewer-trigger='true']").forEach((trigger) => {
    trigger.addEventListener("click", async (event) => {
      const partId = trigger.getAttribute("data-part-id") || "";
      const index = Number.parseInt(trigger.getAttribute("data-image-index") || "0", 10);
      event.preventDefault();
      if (!payload.parts[partId]) {
        await fetchPartPayload(trigger, partId);
      }
      openViewer(partId, Number.isFinite(index) ? index : 0, trigger);
    });
  });

  previousButton.addEventListener("click", () => {
    activeIndex -= 1;
    render();
  });

  nextButton.addEventListener("click", () => {
    activeIndex += 1;
    render();
  });

  closeButton.addEventListener("click", () => {
    dialog.close();
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });

  dialog.addEventListener("close", () => {
    imageNode.removeAttribute("src");
    resetImageSizing();
    imageNode.classList.remove("is-hidden");
    codeBlockNode.classList.add("is-hidden");
    codeNode.textContent = "";
    languageNode.classList.add("is-hidden");
    stateNode.classList.add("is-hidden");
    if (activeTrigger && typeof activeTrigger.focus === "function") {
      activeTrigger.focus();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (!dialog.open) {
      return;
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      activeIndex -= 1;
      render();
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      activeIndex += 1;
      render();
    }
  });

  window.addEventListener("resize", () => {
    if (!dialog.open) {
      return;
    }
    queueImageFit();
  });
});

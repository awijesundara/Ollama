(() => {
  const providers = [
    {
      name: "Ollama",
      model: "Local chat model",
      status: "Connected",
      active: true,
    },
    { name: "ChatGPT", model: "OpenAI models", status: "Setup required" },
    { name: "Claude", model: "Anthropic models", status: "Setup required" },
    { name: "Gemini", model: "Google models", status: "Setup required" },
  ];

  const decorateThinkingCards = () => {
    document.querySelectorAll("strong").forEach((heading) => {
      if (heading.textContent?.trim() !== "Thinking") return;
      const content =
        heading.closest(".prose") ||
        heading.closest('[class*="markdown"]') ||
        heading.parentElement?.parentElement;
      content?.classList.add("thinking-reel");
    });
  };

  const closeProviderMenus = (except) => {
    document.querySelectorAll(".composer-model-menu.is-open").forEach((menu) => {
      if (menu !== except) menu.classList.remove("is-open");
    });
  };

  const createProviderPicker = (textarea) => {
    if (textarea.dataset.modelPickerReady === "true") return;
    const form = textarea.closest("form");
    if (!form) return;
    textarea.dataset.modelPickerReady = "true";
    form.classList.add("composer-with-model-picker");

    const picker = document.createElement("div");
    picker.className = "composer-model-picker";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "composer-model-trigger";
    button.setAttribute("aria-haspopup", "menu");
    button.setAttribute("aria-expanded", "false");
    button.innerHTML =
      '<span class="provider-live-dot"></span><span>Ollama</span><span class="model-chevron">⌄</span>';

    const menu = document.createElement("div");
    menu.className = "composer-model-menu";
    menu.setAttribute("role", "menu");
    menu.innerHTML =
      '<div class="model-menu-title">Choose a model</div>' +
      providers
        .map(
          (provider) => `
            <button type="button" class="model-option${provider.active ? " is-active" : ""}"
              ${provider.active ? "" : "disabled"} role="menuitem">
              <span class="model-option-mark">${provider.active ? "✓" : "⌁"}</span>
              <span class="model-option-copy">
                <strong>${provider.name}</strong>
                <small>${provider.model}</small>
              </span>
              <span class="model-option-status">${provider.status}</span>
            </button>`,
        )
        .join("");

    button.addEventListener("click", () => {
      const opening = !menu.classList.contains("is-open");
      closeProviderMenus(menu);
      menu.classList.toggle("is-open", opening);
      button.setAttribute("aria-expanded", String(opening));
    });
    picker.append(button, menu);
    form.appendChild(picker);
  };

  const enhanceInterface = () => {
    decorateThinkingCards();
    document.querySelectorAll("textarea").forEach(createProviderPicker);
  };

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".composer-model-picker")) closeProviderMenus();
  });

  const observer = new MutationObserver(enhanceInterface);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
  enhanceInterface();
})();

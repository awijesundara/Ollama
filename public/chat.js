(() => {
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
  const observer = new MutationObserver(decorateThinkingCards);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
  decorateThinkingCards();
})();

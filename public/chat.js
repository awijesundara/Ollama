(() => {
  const activityPattern =
    /^(Reading uploaded files|Analyzing uploaded image|Analyzing \d+ uploaded images|Reviewing uploaded documents|Preparing response|Response ready)…?$/;

  const decorateActivityRows = () => {
    document.querySelectorAll("strong").forEach((heading) => {
      if (!activityPattern.test(heading.textContent?.trim() || "")) return;
      const content =
        heading.closest(".prose") ||
        heading.closest('[class*="markdown"]') ||
        heading.parentElement?.parentElement;
      if (!content || content.classList.contains("thinking-reel")) return;
      content.classList.add("thinking-reel");
      const message =
        content.closest('[data-testid*="message"]') ||
        content.closest('[data-step-type]') ||
        content.parentElement?.parentElement;
      message?.classList.add("ghost-activity-message");
    });
  };
  const observer = new MutationObserver(decorateActivityRows);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
  decorateActivityRows();
})();

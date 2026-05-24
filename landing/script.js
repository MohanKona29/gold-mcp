// Tab switcher for install snippets
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.tab;
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.toggle("active", p.id === "tab-" + target);
    });
  });
});

// Copy-to-clipboard on code blocks
document.querySelectorAll(".code-block .copy").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const code = btn.parentElement.querySelector("pre code");
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code.textContent);
      const original = btn.textContent;
      btn.textContent = "copied";
      btn.classList.add("copied");
      setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove("copied");
      }, 1400);
    } catch (e) {
      btn.textContent = "err";
      setTimeout(() => (btn.textContent = "copy"), 1400);
    }
  });
});

// Smooth-scroll for in-page anchors
document.querySelectorAll('a[href^="#"]').forEach((a) => {
  a.addEventListener("click", (e) => {
    const id = a.getAttribute("href").slice(1);
    const el = document.getElementById(id);
    if (!el) return;
    e.preventDefault();
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    history.replaceState(null, "", "#" + id);
  });
});

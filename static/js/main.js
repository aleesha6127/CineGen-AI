// ─── CINEGEN AI — MAIN JS ───────────────────────────────
// Global utilities: Sidebar, Toast, Loading, Auth state

// ─── TOAST NOTIFICATIONS ────────────────────────────────
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icons = { success: "✔", error: "✖", info: "ℹ" };
  toast.innerHTML = `<span>${icons[type] || "ℹ"}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3800);
}
window.showToast = showToast;

// ─── SIDEBAR TOGGLE (MOBILE) ─────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const toggle = document.getElementById("sidebar-toggle");
  const closeBtn = document.getElementById("sidebar-close");

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add("open");
    backdrop && backdrop.classList.add("open");
    document.body.style.overflow = "hidden";
  }
  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    backdrop && backdrop.classList.remove("open");
    document.body.style.overflow = "";
  }
  toggle && toggle.addEventListener("click", openSidebar);
  closeBtn && closeBtn.addEventListener("click", closeSidebar);
  backdrop && backdrop.addEventListener("click", closeSidebar);

  // Close sidebar on nav link click (mobile)
  sidebar && sidebar.querySelectorAll(".sidebar-link").forEach(link => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });

  // ─── AUTO SIGN-OUT LISTENER ──────────────────────────
  // Listen for auth state to ensure session is consistent
  document.addEventListener("authReady", ({ detail: { user } }) => {
    window.__currentUser = user;
    // Update avatar initial if present
    const avatar = document.getElementById("user-avatar");
    const nameEl = document.getElementById("user-name");
    if (user && avatar) {
      avatar.textContent = (user.displayName || user.email || "U")[0].toUpperCase();
    }
    if (user && nameEl) {
      nameEl.textContent = user.displayName || user.email?.split("@")[0] || "Filmmaker";
    }
  });
});

// ─── ANIMATED DOTS (loading text) ───────────────────────
(function animateDots() {
  const dotsEls = document.querySelectorAll(".dots");
  if (!dotsEls.length) return;
  let count = 0;
  setInterval(() => {
    count = (count + 1) % 4;
    dotsEls.forEach(el => { el.textContent = ".".repeat(count + 1); });
  }, 500);
})();

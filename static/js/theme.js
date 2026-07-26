/**
 * Dark/light theme toggle.
 * The initial theme is set synchronously in <head> (see base.html) to avoid
 * a flash of the wrong theme; this file only wires up the toggle button.
 */
(function () {
  const STORAGE_KEY = 'ars-theme';
  const root = document.documentElement;
  const toggleBtn = document.getElementById('themeToggle');

  if (!toggleBtn) return;

  toggleBtn.addEventListener('click', function () {
    const current = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem(STORAGE_KEY, next);
  });
})();

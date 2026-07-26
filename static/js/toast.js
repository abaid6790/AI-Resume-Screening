/**
 * Flash messages render server-side (so they're visible even before this
 * script runs) as .ars-toast elements inside #toastContainer. This adds a
 * staggered slide-in entrance and an auto-dismiss timer as progressive
 * enhancement. Manual closing is left entirely to Bootstrap's own
 * data-bs-dismiss="alert" behavior (already wired via bootstrap.bundle.js)
 * so there's exactly one code path removing a toast, not two racing.
 */
(function () {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('.ars-toast').forEach(function (toast, index) {
    if (!reduceMotion) {
      toast.style.animationDelay = (index * 80) + 'ms';
      toast.classList.add('ars-toast-entering');
    }

    const delay = parseInt(toast.dataset.autodismiss || '0', 10);
    if (delay <= 0 || !window.bootstrap) return;

    let timer = setTimeout(function () {
      bootstrap.Alert.getOrCreateInstance(toast).close();
    }, delay);

    // Don't dismiss out from under someone who's actively reading it.
    toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
  });
})();

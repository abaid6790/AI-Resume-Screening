/**
 * App assistant widget. Talks only to /assistant/ask, which is a rule-based
 * (non-LLM) endpoint that can only reply with canned answers about using
 * this app — see services/assistant_service.py.
 */
(function () {
  const toggle = document.getElementById('arsAssistantToggle');
  const panel = document.getElementById('arsAssistantPanel');
  const closeBtn = document.getElementById('arsAssistantClose');
  const form = document.getElementById('arsAssistantForm');
  const input = document.getElementById('arsAssistantInput');
  const messages = document.getElementById('arsAssistantMessages');

  if (!toggle || !panel || !form || !input || !messages) return;

  function addMessage(text, sender) {
    const el = document.createElement('div');
    el.className = 'ars-assistant-msg ars-assistant-msg-' + sender;
    el.textContent = text;
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function openPanel() {
    panel.classList.remove('d-none');
    toggle.setAttribute('aria-expanded', 'true');
    input.focus();
  }

  function closePanel() {
    panel.classList.add('d-none');
    toggle.setAttribute('aria-expanded', 'false');
  }

  toggle.addEventListener('click', function () {
    if (panel.classList.contains('d-none')) {
      openPanel();
    } else {
      closePanel();
    }
  });

  closeBtn.addEventListener('click', closePanel);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.classList.contains('d-none')) {
      closePanel();
      toggle.focus();
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    input.value = '';
    input.disabled = true;

    fetch('/assistant/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) { addMessage(data.reply, 'bot'); })
      .catch(function () { addMessage('Sorry, something went wrong. Please try again.', 'bot'); })
      .finally(function () {
        input.disabled = false;
        input.focus();
      });
  });
})();

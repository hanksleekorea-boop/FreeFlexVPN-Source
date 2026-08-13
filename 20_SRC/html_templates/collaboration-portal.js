(() => {
  'use strict';
  const form = document.querySelector('#login-form');
  const message = document.querySelector('#message');
  const statusCard = document.querySelector('#status-card');
  const status = document.querySelector('#status');
  let csrfToken = '';
  const safeText = value => JSON.stringify(value, null, 2);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    message.textContent = '로그인 확인 중…';
    const password = form.elements.password.value;
    try {
      const response = await fetch('/api/development/login', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});
      form.reset();
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || '로그인하지 못했습니다.');
      csrfToken = payload.csrf_token;
      const readback = await fetch('/api/development/status', {credentials:'same-origin'});
      const current = await readback.json();
      if (!readback.ok) throw new Error(current.message || '상태를 읽지 못했습니다.');
      status.textContent = safeText(current);
      statusCard.hidden = false;
      message.textContent = '로그인 완료. 서버 연결 상태를 확인했습니다.';
      message.className = 'ok';
    } catch (error) {
      csrfToken = '';
      message.textContent = error instanceof Error ? error.message : '요청을 처리하지 못했습니다.';
      message.className = 'warn';
    }
  });
  window.addEventListener('pagehide', () => { csrfToken = ''; });
})();

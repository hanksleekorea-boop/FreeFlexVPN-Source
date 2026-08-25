(() => {
  'use strict';
  const form = document.querySelector('#login-form');
  const message = document.querySelector('#message');
  const statusCard = document.querySelector('#status-card');
  const status = document.querySelector('#status');
  const capabilityMessage = document.querySelector('#capability-message');
  const workspaceCard = document.querySelector('#workspace-card');
  const integrationCard = document.querySelector('#integration-card');
  const workspaceMessage = document.querySelector('#workspace-message');
  const integrationMessage = document.querySelector('#integration-message');
  let csrfToken = '';
  let revision = '';
  const safeText = value => JSON.stringify(value, null, 2);
  const operationId = prefix => `${prefix}.${crypto.randomUUID()}`;
  const api = async (path, options = {}) => {
    const headers = {...(options.headers || {})};
    if (options.body) headers['Content-Type'] = 'application/json';
    if (options.method && options.method !== 'GET') headers['X-FreeFlex-CSRF'] = csrfToken;
    const response = await fetch(path, {...options, headers, credentials:'same-origin'});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || '요청을 처리하지 못했습니다.');
    return payload;
  };
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
      const manifest = await api('/.well-known/ai-development.json');
      workspaceCard.hidden = !manifest.capabilities.write;
      integrationCard.hidden = !manifest.capabilities.integration_request;
      capabilityMessage.textContent = manifest.capabilities.integration_request
        ? '세션별 격리 편집과 소유자 검토 요청이 연결됐습니다.'
        : '편집 또는 GitHub 통합 중계가 아직 연결되지 않았습니다.';
      capabilityMessage.className = manifest.capabilities.integration_request ? 'ok' : 'warn';
      message.textContent = '로그인 완료. 서버 연결 상태를 확인했습니다.';
      message.className = 'ok';
    } catch (error) {
      csrfToken = '';
      message.textContent = error instanceof Error ? error.message : '요청을 처리하지 못했습니다.';
      message.className = 'warn';
    }
  });
  document.querySelector('#read-file').addEventListener('click', async () => {
    try {
      const path = document.querySelector('#file-path').value;
      const payload = await api(`/api/development/read?path=${encodeURIComponent(path)}`);
      document.querySelector('#file-content').value = payload.content; revision = payload.revision;
      workspaceMessage.textContent = `최신판을 읽었습니다 (${payload.bytes} bytes).`;
      workspaceMessage.className = 'ok';
    } catch (error) { workspaceMessage.textContent = error.message; workspaceMessage.className = 'warn'; }
  });
  document.querySelector('#save-file').addEventListener('click', async () => {
    try {
      if (!revision) throw new Error('먼저 최신 파일을 읽으세요.');
      const payload = await api('/api/development/write', {method:'PUT',body:JSON.stringify({
        operation_id: operationId('workspace.write'), path:document.querySelector('#file-path').value,
        content:document.querySelector('#file-content').value, expected_revision:revision,
      })});
      revision = payload.revision; workspaceMessage.textContent = payload.changed ? '격리 작업공간에 저장했습니다.' : '내용이 같아 변경하지 않았습니다.';
      workspaceMessage.className = 'ok';
    } catch (error) { workspaceMessage.textContent = error.message; workspaceMessage.className = 'warn'; }
  });
  document.querySelector('#commit-file').addEventListener('click', async () => {
    try {
      const payload = await api('/api/development/commit', {method:'POST',body:JSON.stringify({
        operation_id:operationId('workspace.commit'), message:document.querySelector('#commit-message').value,
        paths:[document.querySelector('#file-path').value],
      })});
      workspaceMessage.textContent = `커밋 완료: ${payload.commit_sha.slice(0, 12)}`; workspaceMessage.className = 'ok';
    } catch (error) { workspaceMessage.textContent = error.message; workspaceMessage.className = 'warn'; }
  });
  document.querySelector('#request-integration').addEventListener('click', async () => {
    try {
      const payload = await api('/api/development/integration-request', {method:'POST',body:JSON.stringify({
        operation_id:operationId('workspace.integration'), title:document.querySelector('#pr-title').value,
        body:document.querySelector('#pr-body').value,
      })});
      integrationMessage.textContent = `검토 요청 #${payload.pull_request_number} 생성 완료.`; integrationMessage.className = 'ok';
    } catch (error) { integrationMessage.textContent = error.message; integrationMessage.className = 'warn'; }
  });
  window.addEventListener('pagehide', () => { csrfToken = ''; });
})();

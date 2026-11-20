const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, Project, fixtures } = require('../../../helpers/live');

test('[SHARE-01,SHARE-03] read-only share blocks writes and revocation blocks new reads', async () => {
  const p = await project(), guest = await account();
  const share = success(await p.mutate('POST', '/share', { permission: 'read' }));
  const route = `/api-gateway/projects/${guest.id}/${p.id}?owner=${p.user.id}&share=${share.id}`;
  assert.equal(success(await request('GET', route, { token: guest.token }))._id, p.id);
  for (const [method, suffix, body] of [['PUT', '', { name: 'forbidden' }], ['POST', '/tool', { procedure: 'rotate', params: { angle: 90 } }], ['POST', '/process', {}]]) {
    const url = route.replace('?', suffix + '?');
    const r = await request(method, url, { token: guest.token, body, headers: { 'X-Project-Version': String((await p.get()).version) } });
    assert.equal(r.status, 403, `${method} ${suffix}`);
  }
  success(await p.mutate('DELETE', `/share/${share.id}`));
  assert.equal((await request('GET', route, { token: guest.token })).status, 410);
});

test('[SHARE-01] edit share can rename and persists the change for the owner', async () => {
  const p = await project(), guest = await account();
  const share = success(await p.mutate('POST', '/share', { permission: 'edit' }));
  const r = await request('PUT', `/api-gateway/projects/${guest.id}/${p.id}?owner=${p.user.id}&share=${share.id}`, {
    token: guest.token, body: { name: 'Guest edit' }, headers: { 'X-Project-Version': String((await p.get()).version) },
  });
  success(r); assert.equal((await p.get()).name, 'Guest edit');
});

test('[SHARE-02,CONC-03] two editors with the same version cannot silently overwrite each other', async () => {
  const p = await project(), guest = await account();
  const share = success(await p.mutate('POST', '/share', { permission: 'edit' }));
  const version = (await p.get()).version;
  const responses = await Promise.all([
    request('PUT', p.route, { token: p.user.token, body: { name: 'Owner edit' }, headers: { 'X-Project-Version': String(version) } }),
    request('PUT', `/api-gateway/projects/${guest.id}/${p.id}?owner=${p.user.id}&share=${share.id}`, { token: guest.token, body: { name: 'Guest edit' }, headers: { 'X-Project-Version': String(version) } }),
  ]);
  assert.deepEqual(responses.map(r => r.status).sort(), [204, 409]);
  const winner = responses[0].status === 204 ? 'Owner edit' : 'Guest edit';
  assert.equal((await p.get()).name, winner);
});

test('[SHARE-02] free owner allows two active editors and rejects a third', async () => {
  const p = await project(), guest = await account(), third = await account();
  const share = success(await p.mutate('POST', '/share', { permission: 'edit' }));
  const route = user => `/api-gateway/projects/${user.id}/${p.id}?owner=${p.user.id}&share=${share.id}`;
  success(await request('GET', route(guest), { token: guest.token }));
  assert.equal((await request('GET', route(third), { token: third.token })).status, 429);
});

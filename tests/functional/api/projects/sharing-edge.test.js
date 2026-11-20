const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, fixtures, fixture, db, dockerNode } = require('../../../helpers/live');

test('[SHARE-03,ASSIST-01] coverage: read share cannot request suggestions or create sharing permissions', async () => {
  const p = await project(), guest = await account();
  success(await p.upload(fixture('pattern.png')));
  const link = success(await p.mutate('POST', '/share', { permission: 'read' }));
  const suffix = `?owner=${p.user.id}&share=${link.id}`;
  assert.equal((await request('POST', `/api-gateway/projects/${guest.id}/${p.id}/assistant/suggest${suffix}`, {
    token: guest.token, body: { message: 'brighter' }, headers: { 'X-Project-Version': String((await p.get()).version) },
  })).status, 403);
  assert.equal((await request('POST', `${p.route}/share?share=${link.id}`, {
    token: guest.token, body: { permission: 'edit' }, headers: { 'X-Project-Version': String((await p.get()).version) },
  })).status, 403);
});

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { request, success, account, project, db } = require('../../../helpers/live');

test('[AUTH-01] registration and login preserve identity and reject wrong credentials', async () => {
  const a = await account();
  const logged = success(await request('POST', `/api-gateway/users/${a.email}/login`, { body: { password: a.password } }));
  assert.equal(logged.user._id, a.id);
  assert.equal(logged.user.email, a.email);
  assert.equal(logged.user.password_hash, undefined);
  assert.equal((await request('POST', `/api-gateway/users/${a.email}/login`, { body: { password: 'incorrect' } })).status, 401);
});

test('[AUTH-02] missing, invalid and foreign JWTs cannot read or change a project', async () => {
  const a = await account(), b = await account(), p = await project(a);
  for (const token of [undefined, 'invalid', b.token]) {
    for (const method of ['GET', 'PUT', 'DELETE']) {
      const r = await request(method, p.route, { token, body: method === 'PUT' ? { name: 'unauthorized' } : undefined, headers: { 'X-Project-Version': '0' } });
      assert.ok([401, 403].includes(r.status), `${method}: ${r.status}`);
    }
  }
  assert.equal((await p.get()).name, 'Regression project');
});

test('[AUTH-03.3] deleting an account prevents a new login', async () => {
  const a = await account();
  success(await request('DELETE', `/api-gateway/users/${a.id}`, { token: a.token }));
  assert.equal((await request('POST', `/api-gateway/users/${a.email}/login`, { body: { password: a.password } })).status, 401);
  assert.equal(db('users', a.id), null);
});

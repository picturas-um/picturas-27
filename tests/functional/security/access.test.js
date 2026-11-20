const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, fixtures, fixture, dockerNode, db } = require('../../helpers/live');
const { socket, event } = require('../../helpers/media');

test('[AUTH-02] expired signed JWT cannot access a project', async () => {
  const p = await project();
  const expired = dockerNode('users', "console.log(require('jsonwebtoken').sign({id:process.argv[1]},process.env.JWT_SECRET_KEY,{expiresIn:-1}))", [p.user.id]).trim();
  assert.equal((await request('GET', p.route, { token: expired })).status, 401);
});





test('[STORE-01,OUT-01] foreign user cannot obtain originals or results through the gateway', async () => {
  const p = await project(), other = await account();
  success(await p.upload(fixture('pattern.png')));
  for (const suffix of ['/imgs', '/process/url', '/process']) {
    assert.ok([401, 403].includes((await request('GET', p.route + suffix, { token: other.token })).status));
  }
});



test('[STORE-01] tampering with the object key invalidates a signed URL', async () => {
  const p = await project(); success(await p.upload(fixture('pattern.png')));
  const imgs = success(await request('GET', p.route + '/imgs', { token: p.user.token }));
  const url = new URL(imgs[0].url); url.pathname += '-tampered';
  assert.ok((await request('GET', url.toString())).status >= 400);
});

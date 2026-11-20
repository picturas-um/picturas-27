const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, fixtures, fixture, db, dockerNode } = require('../../helpers/live');

test('[CONC-02,CONC-04] coverage: duplicate processing requests cannot start two active runs', { timeout: 120000 }, async () => {
  const p = await project(); success(await p.upload(fixture('pattern.png')));
  await p.tools([{ procedure: 'resize', params: { width: 80, height: 60 } }]);
  const version = (await p.get()).version;
  const options = { token: p.user.token, body: {}, headers: { 'X-Project-Version': String(version) } };
  const responses = await Promise.all([request('POST', p.route + '/process', options), request('POST', p.route + '/process', options)]);
  assert.deepEqual(responses.map(x => x.status).sort(), [201, 409]);
});

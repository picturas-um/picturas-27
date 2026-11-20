const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, Project, fixtures, fixture } = require('../../../helpers/live');

test('[PIPE-02] invalid tool requests do not change the project', async () => {
  const p = await project();
  assert.equal((await p.mutate('POST', '/tool', { procedure: 'resize' })).status, 400);
  assert.equal((await p.mutate('POST', '/tool', { procedure: 'extract_frames', params: { count: 101, mode: 'count', format: 'png' } })).status, 400);
  assert.equal((await p.get()).tools.length, 0);
});
test('[VID-05.1] API prevents duplicate and nonterminal frame extraction', async () => {
  const p = await project();
  const extraction = { procedure: 'extract_frames', params: { mode: 'count', count: 2, format: 'png' } };
  success(await p.mutate('POST', '/tool', extraction));
  success(await p.mutate('POST', '/tool', { procedure: 'brightness', params: { brightness: 0.2 } }));
  const saved = await p.get();
  assert.equal(saved.tools.at(-1).procedure, 'extract_frames');
  assert.equal((await p.mutate('POST', '/tool', extraction)).status, 400);
  assert.equal((await p.mutate('POST', '/reorder', [...saved.tools].reverse())).status, 400);
});
test('[CONC-04] retry with a stale version cannot duplicate a tool', async () => {
  const p = await project(), version = (await p.get()).version;
  const options = { token: p.user.token, body: { procedure: 'rotate', params: { angle: 90 } }, headers: { 'X-Project-Version': String(version) } };
  success(await request('POST', p.route + '/tool', options));
  assert.equal((await request('POST', p.route + '/tool', options)).status, 409);
  assert.equal((await p.get()).tools.length, 1);
});

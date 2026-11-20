const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, Project, fixtures, fixture } = require('../../../helpers/live');

test('[PROJ-01] create list rename reopen and delete a project', async () => {
  const p = await project(), a = p.user;
  const list = success(await request('GET', `/api-gateway/projects/${a.id}`, { token: a.token }));
  assert.ok(list.some(x => x._id === p.id));
  success(await p.mutate('PUT', '', { name: 'Renamed regression' }));
  assert.equal((await p.get()).name, 'Renamed regression');
  success(await p.mutate('DELETE'));
  assert.ok((await request('GET', p.route, { token: a.token })).status >= 400);
});
test('[PIPE-01] add edit reorder and remove tools persists pipeline order', async () => {
  const p = await project();
  success(await p.mutate('POST', '/tool', { procedure: 'brightness', params: { brightness: 0.2 } }));
  success(await p.mutate('POST', '/tool', { procedure: 'rotate', params: { angle: 90 } }));
  let saved = await p.get();
  success(await p.mutate('PUT', `/tool/${saved.tools[0]._id}`, { params: { brightness: 0.4 } }));
  assert.equal((await p.get()).tools[0].params.brightness, 0.4);
  await p.tools([...saved.tools].reverse());
  saved = await p.get();
  assert.deepEqual(saved.tools.map(x => x.procedure), ['rotate', 'brightness']);
  success(await p.mutate('DELETE', `/tool/${saved.tools[0]._id}`));
  assert.deepEqual((await p.get()).tools.map(x => x.procedure), ['brightness']);
});
test('[PROJ-02,STORE-02] deleting one media item preserves the other original', async () => {
  const p = await project();
  success(await p.upload(fixture('pattern.png')));
  success(await p.upload(fixture('pattern.jpg')));
  const saved = await p.get();
  const removedUrl = saved.imgs[0].url;
  success(await p.mutate('DELETE', `/img/${saved.imgs[0]._id}`));
  const after = await p.get();
  assert.equal(after.imgs.length, 1); assert.equal(after.imgs[0]._id, saved.imgs[1]._id);
  assert.ok((await request('GET', removedUrl)).status >= 400, 'Removed source must disappear from storage');
});

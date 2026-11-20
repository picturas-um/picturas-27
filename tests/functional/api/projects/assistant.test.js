const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, Project, fixtures, fixture } = require('../../../helpers/live');

test('[ASSIST-01] suggestions are editable valid pipelines without changing the project', async () => {
  const p = await project(); success(await p.upload(fixture('pattern.png')));
  const before = await p.get();
  const result = success(await p.mutate('POST', '/assistant/suggest', { message: 'make this brighter', currentTools: [], imgId: before.imgs[0]._id }));
  assert.ok(result.suggestions.length > 0);
  assert.ok(result.suggestions.every(s => s.tools.length > 0));
  assert.deepEqual((await p.get()).tools, before.tools);
  await p.tools(result.suggestions[0].tools);
  assert.ok((await p.get()).tools.length > 0);
});

test('[ASSIST-01] assistant rejects empty message and empty project', async () => {
  const p = await project();
  assert.equal((await p.mutate('POST', '/assistant/suggest', { message: '' })).status, 400);
  assert.equal((await p.mutate('POST', '/assistant/suggest', { message: 'make brighter' })).status, 400);
});

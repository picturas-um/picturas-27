const { test } = require('node:test');
const assert = require('node:assert/strict');
const { request, success, account, project, db } = require('../../../helpers/live');

const tools = [{ procedure: 'brightness', params: { brightness: 0.3 } }, { procedure: 'rotate', params: { angle: 90 } }];

test('[PRESET-01.1] save ordered tools and reject incomplete presets', async () => {
  const a = await account(), route = `/api-gateway/users/${a.id}/presets`;
  const preset = success(await request('POST', route, { token: a.token, body: { name: 'Test preset', tools } }));
  assert.deepEqual(preset.tools.map(({ procedure, params }) => ({ procedure, params })), tools);
  assert.equal((await request('POST', route, { token: a.token, body: { name: 'Invalid', tools: tools.slice(0, 1) } })).status, 400);
});

test('[PRESET-01.2] update a preset and apply its saved tools to a project', async () => {
  const a = await account(), route = `/api-gateway/users/${a.id}/presets`, p = await project(a);
  const preset = success(await request('POST', route, { token: a.token, body: { name: 'Test preset', tools } }));
  const saved = success(await request('PATCH', `${route}/${preset._id}`, { token: a.token, body: { name: 'Updated', tools: [...tools].reverse() } }));
  await p.tools(saved.tools);
  assert.deepEqual((await p.get()).tools.map(t => t.procedure), ['rotate', 'brightness']);
  const listed = success(await request('GET', route, { token: a.token }));
  assert.equal(listed.userPresets[0].name, 'Updated');
});

test('[PRESET-01.3] share and delete a preset without permitting foreign edits', async () => {
  const a = await account(), b = await account(), route = `/api-gateway/users/${a.id}/presets`;
  const preset = success(await request('POST', route, { token: a.token, body: { name: 'Shared', tools } }));
  const shared = success(await request('POST', `${route}/${preset._id}/share`, { token: a.token, body: {} }));
  assert.ok(shared.shareId);
  const read = success(await request('GET', `/api-gateway/users/presets/share/${shared.shareId}`));
  assert.equal(read.name, 'Shared');
  assert.ok((await request('DELETE', `${route}/${preset._id}`, { token: b.token })).status >= 400);
  success(await request('DELETE', `${route}/${preset._id}`, { token: a.token }));
  assert.equal(success(await request('GET', route, { token: a.token })).userPresets.length, 0);
});

test('[PRESET-01.4] a fifth preset cannot change the four saved presets', async () => {
  const a = await account(), route = `/api-gateway/users/${a.id}/presets`;
  for (let i = 0; i < 4; i++) success(await request('POST', route, { token: a.token, body: { name: `Preset ${i}`, tools } }));
  assert.equal((await request('POST', route, { token: a.token, body: { name: 'Fifth', tools } })).status, 409);
  assert.equal(success(await request('GET', route, { token: a.token })).userPresets.length, 4);
});

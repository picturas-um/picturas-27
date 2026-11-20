const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, fixtures, fixture, db, dockerNode } = require('../../helpers/live');

test('[PLAN-02] coverage: advanced image operations are counted per image', { timeout: 120000 }, async () => {
  const p = await project();
  for (const name of ['a.png', 'b.png']) success(await p.upload(fixture('pattern.png'), 'img', name));
  await p.tools([{ procedure: 'upgrade_ai', params: {} }]);
  assert.equal((await p.process()).imgs.length, 2);
  assert.equal(db('users', p.user.id).operations.reduce((n, x) => n + x.processed, 0), 2);
});

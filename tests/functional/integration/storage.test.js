const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, fixtures, fixture, db, dockerNode } = require('../../helpers/live');

test('[STORE-02] coverage: copies and deletes work in every storage stage', async () => {
  const p = await project(); success(await p.upload(fixture('pattern.png')));
  const item = db('projects', p.user.id, 'findOne', null, 'projects').imgs[0];
  const prefix = `${p.user.id}/${p.id}`, original = require('node:fs').readFileSync(fixture('pattern.png'));
  for (const stage of ['preview', 'preview_cache', 'out']) {
    success(await request('POST', `http://localhost:11000/copy/${prefix}/src/${stage}/${item.og_img_key}`, { body: {} }));
    const url = success(await request('GET', `http://localhost:11000/image/public/${prefix}/${stage}/${item.og_img_key}`)).url;
    assert.deepEqual((await request('GET', url)).buffer, original);
    success(await request('DELETE', `http://localhost:11000/delete/${prefix}/${stage}/${item.og_img_key}`));
    assert.ok((await request('GET', url)).status >= 400);
  }
  assert.equal((await p.get()).imgs.length, 1);
});

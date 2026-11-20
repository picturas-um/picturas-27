const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, Project, fixtures, fixture } = require('../../../helpers/live');

test('[UP-01] a PNG upload preserves bytes and source identity', async () => {
  const p = await project(); success(await p.upload(fixture('pattern.png')));
  const saved = await p.get(); assert.equal(saved.imgs.length, 1);
  assert.equal(saved.imgs[0].media_type, 'image');
  const urls = success(await request('GET', p.route + '/imgs', { token: p.user.token }));
  assert.equal(urls.length, 1);
  const downloaded = await request('GET', urls[0].url);
  assert.deepEqual(downloaded.buffer, require('node:fs').readFileSync(fixture('pattern.png')));
});

test('[UP-01] image endpoint rejects a video upload', async () => {
  const p = await project();
  const r = await p.upload(fixture('clip.mp4'));
  assert.ok(r.status >= 400 && r.status < 500, `clip.mp4: ${r.status}`);
  assert.equal((await p.get()).imgs.length, 0);
});

test('[EDGE-01] duplicate image name is rejected', async () => {
  const p = await project();
  success(await p.upload(fixture('pattern.png'), 'img', 'duplicate.png'));
  assert.equal((await p.upload(fixture('pattern.png'), 'img', 'duplicate.png')).status, 400);
  assert.equal((await p.get()).imgs.length, 1);
});

test('[UP-02.2] video endpoint accepts video metadata and rejects wrong media or corruption', async () => {
  const p = await project();
  success(await p.upload(fixture('clip.mp4'), 'video'));
  const saved = await p.get();
  assert.equal(saved.imgs[0].media_type, 'video');
  assert.equal(saved.imgs[0].video.video_codec, 'h264');
  assert.ok(Math.abs(saved.imgs[0].video.duration - 4) < 0.2);
  for (const file of ['pattern.png', 'corrupt.mp4', 'long.mp4']) {
    const r = await p.upload(fixture(file), 'video');
    assert.ok(r.status >= 400 && r.status < 500, `${file}: ${r.status}`);
    assert.equal((await p.get()).imgs.length, 1);
  }
});

test('[PLAN-01] anonymous video upload is rejected and basic image tools remain available', async () => {
  const p = await project(await account('anonymous'));
  assert.equal((await p.upload(fixture('clip.mp4'), 'video')).status, 400);
  success(await p.upload(fixture('pattern.png')));
  success(await p.mutate('POST', '/tool', { procedure: 'brightness', params: { brightness: 0.2 } }));
  assert.equal((await p.mutate('POST', '/tool', { procedure: 'bg_remove_ai', params: {} })).status, 403);
});

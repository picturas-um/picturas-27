const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { request, success, account, project, fixtures, fixture, download, db, until } = require('../../helpers/live');
const { temp, imageInfo, probe, socket, event, preview } = require('../../helpers/media');

test('[IMG-01,RUN-01,OUT-01] real image batch applies ordered effects to both originals', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  for (const name of ['first.png', 'second.png']) success(await p.upload(fixture('pattern.png'), 'img', name));
  await p.tools([{ procedure: 'brightness', params: { brightness: 0.5 } }, { procedure: 'border', params: { borderWidth: 2, r: 255, g: 0, b: 0 } }]);
  const results = await p.process(); assert.equal(results.imgs.length, 2);
  assert.equal(new Set(results.imgs.map(x => x.og_img_id)).size, 2);
  for (let i = 0; i < results.imgs.length; i++) {
    const out = path.join(dir, `${i}.png`); await download(results.imgs[i].url, out);
    const info = imageInfo(out); assert.deepEqual(info.size, [164, 124]); assert.deepEqual(info.corner, [255, 0, 0]);
    assert.ok(info.mean[1] < imageInfo(fixture('pattern.png')).mean[1]);
  }
  const originals = success(await request('GET', p.route + '/imgs', { token: p.user.token }));
  for (const original of originals) assert.deepEqual((await request('GET', original.url)).buffer, fs.readFileSync(fixture('pattern.png')));
  assert.equal(db('users', p.user.id).operations.length, 0, 'Basic image effects do not consume quota');
});

test('[VID-01,VID-02,EDGE-02] real video trim and speed preserve audio and source', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  success(await p.upload(fixture('clip.mp4'), 'video'));
  const source = (await p.get()).imgs[0];
  await p.tools([{ procedure: 'trim', params: { imgId: source._id, start: 0, end: 2 } }, { procedure: 'speed', params: { imgId: source._id, factor: 2 } }]);
  const results = await p.process(); assert.equal(results.imgs.length, 1);
  const output = path.join(dir, 'out.mp4'); await download(results.imgs[0].url, output);
  const meta = probe(output);
  assert.equal(meta.streams.find(s => s.codec_type === 'video').codec_name, 'h264');
  assert.equal(meta.streams.find(s => s.codec_type === 'audio').codec_name, 'aac');
  assert.ok(Math.abs(Number(meta.format.duration) - 1) < 0.2);
  const urls = success(await request('GET', p.route + '/imgs', { token: p.user.token }));
  assert.deepEqual((await request('GET', urls[0].url)).buffer, fs.readFileSync(fixture('clip.mp4')));
});

test('[VID-03] preview is limited to three seconds and emits video progress', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  success(await p.upload(fixture('clip.mp4'), 'video'));
  await p.tools([{ procedure: 'brightness', params: { brightness: 0.5 } }]);
  const s = await socket(t, p.user.token), progress = [];
  s.on('video-progress', x => progress.push(x));
  const result = await preview(t, p, (await p.get()).imgs[0]._id);
  const out = path.join(dir, 'preview.mp4'); await download(result.imageUrl, out);
  assert.ok(Number(probe(out).format.duration) <= 3.2);
  assert.ok(progress.some(x => x.projectId === p.id && x.percent === 100));
});

test('[VID-04] subtitles on a silent video are a no-op with valid output', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  success(await p.upload(fixture('silent.mov'), 'video'));
  await p.tools([{ procedure: 'subtitles', params: {} }]);
  const result = await p.process(), out = path.join(dir, 'out.mp4');
  await download(result.imgs[0].url, out);
  assert.ok(Math.abs(Number(probe(out).format.duration) - 2) < 0.2);
  assert.equal(probe(out).streams.some(x => x.codec_type === 'audio'), false);
});

test('[VID-05.2,VID-05.3,OUT-03] extracted frames and preview belong to edited timeline and ZIP', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  success(await p.upload(fixture('clip.mp4'), 'video'));
  const id = (await p.get()).imgs[0]._id;
  await p.tools([{ procedure: 'resize', params: { width: 80, height: 60 } }, { procedure: 'extract_frames', params: { mode: 'count', count: 3, format: 'png' } }]);
  const previewed = await preview(t, p, id), sheet = path.join(dir, 'sheet.png');
  await download(previewed.imageUrl, sheet); assert.ok(imageInfo(sheet).size[0] > 80);
  const result = await p.process(); assert.equal(result.imgs.length, 3);
  assert.equal(new Set(result.imgs.map(x => x.result_id)).size, 3);
  for (let i = 0; i < 3; i++) {
    assert.equal(result.imgs[i].og_img_id, id);
    const file = path.join(dir, `frame${i}.png`); await download(result.imgs[i].url, file);
    assert.deepEqual(imageInfo(file).size, [80, 60]);
  }
  const zipResponse = await request('GET', p.route + '/process', { token: p.user.token }); success(zipResponse);
  const zip = await require('jszip').loadAsync(zipResponse.buffer);
  assert.deepEqual(Object.keys(zip.files).sort(), result.imgs.map(x => x.name).sort());
});

test('[STORE-02,IMG-02] changing pipeline invalidates image preview', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  success(await p.upload(fixture('pattern.png')));
  const id = (await p.get()).imgs[0]._id;
  await p.tools([{ procedure: 'resize', params: { width: 80, height: 60 } }]);
  const first = await preview(t, p, id); await download(first.imageUrl, path.join(dir, 'first.png'));
  await p.tools([{ procedure: 'resize', params: { width: 40, height: 30 } }]);
  const second = await preview(t, p, id); await download(second.imageUrl, path.join(dir, 'second.png'));
  assert.deepEqual(imageInfo(path.join(dir, 'first.png')).size, [80, 60]);
  assert.deepEqual(imageInfo(path.join(dir, 'second.png')).size, [40, 30]);
});

test('[PROJ-02,STORE-02] clearing a processed project removes edits and results while keeping originals', { timeout: 120000 }, async () => {
  const p = await project(); success(await p.upload(fixture('pattern.png')));
  await p.tools([{ procedure: 'resize', params: { width: 80, height: 60 } }]);
  const results = await p.process();
  success(await p.mutate('POST', '/clear', {}));
  const saved = await p.get(); assert.equal(saved.tools.length, 0); assert.equal(saved.imgs.length, 1);
  assert.equal(success(await request('GET', p.route + '/process/url', { token: p.user.token })).imgs.length, 0);
  assert.ok((await request('GET', results.imgs[0].url)).status >= 400);
  assert.equal((await request('GET', saved.imgs[0].url)).status, 200);
});

test('[VID-02,EDGE-02] mixed media applies trim to one video and common effects to all items', { timeout: 120000 }, async t => {
  const p = await project(), dir = temp(t);
  for (const name of ['a.mp4', 'b.mp4']) success(await p.upload(fixture('clip.mp4'), 'video', name));
  success(await p.upload(fixture('pattern.png')));
  const saved = await p.get(), target = saved.imgs[0]._id;
  await p.tools([{ procedure: 'resize', params: { width: 80, height: 60 } }, { procedure: 'trim', params: { imgId: target, start: 0, end: 2 } }]);
  const result = await p.process(); assert.equal(result.imgs.length, 3);
  for (const [i, item] of result.imgs.entries()) {
    const video = saved.imgs.find(x => x._id === item.og_img_id).media_type === 'video';
    const file = path.join(dir, `${i}.${video ? 'mp4' : 'png'}`); await download(item.url, file);
    if (video) {
      const meta = probe(file), stream = meta.streams.find(x => x.codec_type === 'video');
      assert.deepEqual([stream.width, stream.height], [80, 60]);
      assert.ok(Math.abs(Number(meta.format.duration) - (item.og_img_id === target ? 2 : 4)) < 0.2);
    } else assert.deepEqual(imageInfo(file).size, [80, 60]);
  }
});



test('[CONC-02] concurrent project runs keep their output dimensions isolated', { timeout: 120000 }, async t => {
  const a = await account(), p = await project(a), q = await project(a), dir = temp(t);
  for (const item of [p, q]) success(await item.upload(fixture('pattern.png')));
  await p.tools([{ procedure: 'resize', params: { width: 40, height: 30 } }]);
  await q.tools([{ procedure: 'resize', params: { width: 80, height: 60 } }]);
  const results = await Promise.all([p.process(), q.process()]);
  for (let i = 0; i < 2; i++) {
    const out = path.join(dir, `${i}.png`); await download(results[i].imgs[0].url, out);
    assert.deepEqual(imageInfo(out).size, i === 0 ? [40, 30] : [80, 60]);
  }
});

test('[RUN-02] a failed video stage reports an error without replacing committed results', { timeout: 120000 }, async t => {
  const p = await project();
  success(await p.upload(fixture('silent.mov'), 'video'));
  await p.tools([{ procedure: 'brightness', params: { brightness: 0.5 } }]);
  const previous = await p.process(), committed = db('projects', p.user.id, 'findOne', null, 'projects').committedToken;
  await p.tools([{ procedure: 'resize', params: { width: -1, height: -1 } }]);
  const s = await socket(t, p.user.token), failed = event(s, 'process-error');
  success(await p.mutate('POST', '/process', {})); await failed;
  assert.equal(db('projects', p.user.id, 'findOne', null, 'projects').committedToken, committed);
  const after = success(await request('GET', p.route + '/process/url', { token: p.user.token }));
  assert.deepEqual(after.imgs.map(x => x.result_id), previous.imgs.map(x => x.result_id));
});

const effects = [
  ['binarization', { threshold: 100 }], ['border', { borderWidth: 2, r: 255, g: 0, b: 0 }],
  ['brightness', { brightness: 0.5 }], ['contrast', { contrastFactor: 1.5 }],
  ['cut', { left: 0, top: 0, right: 80, bottom: 60 }], ['resize', { width: 80, height: 60 }],
  ['rotate', { degrees: 90 }], ['saturation', { saturationFactor: 0 }], ['watermark', {}],
  ['bg_remove_ai', {}], ['cut_ai', {}], ['obj_ai', {}], ['people_ai', {}], ['upgrade_ai', {}],
  ['expand_ai', { mode: 'generative', percent: 10, seed: 42, timeoutSec: 30 }], ['text_ai', {}],
];
for (const [procedure, params] of effects) {
  test(`[IMG-02${procedure === 'text_ai' ? ',OUT-04' : ''}] real image worker ${procedure} produces a decodable result`, { timeout: 120000 }, async t => {
    const a = await account(); db('users', a.id, 'updateOne', { type: 'premium' });
    const p = await project(a), dir = temp(t);
    success(await p.upload(fixture(procedure === 'text_ai' ? 'text.png' : 'pattern.png')));
    await p.tools([{ procedure, params }]);
    const results = await p.process();
    if (['text_ai', 'obj_ai', 'people_ai'].includes(procedure)) {
      assert.ok(results.texts.length > 0);
      const r = await request('GET', results.texts[0].url); success(r);
      if (procedure === 'text_ai') assert.match(r.buffer.toString(), /PICTURAS|TEST|123/i);
      else assert.match(r.buffer.toString(), /^class,confidence,bx,by,bw,bh/);
    } else {
      assert.equal(results.imgs.length, 1);
      const out = path.join(dir, 'out.png'); await download(results.imgs[0].url, out);
      const info = imageInfo(out); assert.ok(info.size[0] > 0 && info.size[1] > 0);
      if (['resize', 'cut'].includes(procedure)) assert.deepEqual(info.size, [80, 60]);
      if (procedure === 'rotate') assert.deepEqual(info.size, [120, 160]);
      if (procedure === 'brightness') assert.ok(info.mean[0] < imageInfo(fixture('pattern.png')).mean[0]);
    }
  });
}

test('[VID-04] real speech recognition burns visible captions into video', { timeout: 300000 }, async t => {
  const p = await project(), dir = temp(t);
  success(await p.upload(fixture('speech.mp4'), 'video'));
  await p.tools([{ procedure: 'subtitles', params: {} }]);
  const results = await p.process(240000), out = path.join(dir, 'captions.mp4');
  await download(results.imgs[0].url, out);
  assert.ok(probe(out).streams.some(x => x.codec_type === 'audio'));
  const { execFileSync } = require('node:child_process');
  const brightness = [];
  for (const second of [1, 2, 3, 4, 5]) {
    const file = path.join(dir, `frame-${second}.png`);
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-ss', String(second), '-i', out, '-frames:v', '1', file]);
    brightness.push(imageInfo(file).mean.reduce((a, b) => a + b, 0));
  }
  assert.ok(Math.max(...brightness) > 0.5, 'Captions should produce visible pixels on the black source video');
});

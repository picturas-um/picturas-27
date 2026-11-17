const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createProcessingState, processingStatus, createStatusHandler } = require('../utils/processingStatus');

function fixture() {
  return {
    user_id: 'owner', _id: 'project', version: 4, activeToken: 7,
    processingState: createProcessingState({ token: 7, runnerId: 'owner', totalSteps: 3, videoIds: ['video'] }),
  };
}

// Exercise the real controller against a small Mongo update adapter. No browser
// state participates: loading a fresh copy of the document must recover the run.
async function withController(project, action) {
  const modelPath = require.resolve('../models/project');
  const controllerPath = require.resolve('../controllers/project');
  const oldModel = require.cache[modelPath], oldController = require.cache[controllerPath];
  const get = key => key.split('.').reduce((value, part) => value?.[part], project);
  function set(key, value) {
    const parts = key.split('.'), last = parts.pop();
    let target = project;
    for (const part of parts) target = target[part] ||= {};
    target[last] = structuredClone(value);
  }
  function apply(filter, update) {
    if (!Object.entries(filter).every(([key, value]) => get(key) === value)) return null;
    for (const [key, value] of Object.entries(update.$set || {})) set(key, value);
    for (const [key, value] of Object.entries(update.$inc || {})) set(key, get(key) + value);
    for (const [key, value] of Object.entries(update.$max || {})) set(key, Math.max(get(key) || 0, value));
    for (const [key, value] of Object.entries(update.$addToSet || {})) {
      const values = get(key) || [];
      if (!values.includes(value)) set(key, [...values, value]);
    }
    return structuredClone(project);
  }
  require.cache[modelPath] = { id: modelPath, filename: modelPath, loaded: true, exports: {
    findOneAndUpdate: (filter, update) => ({ exec: async () => apply(filter, update) }),
    updateOne: (filter, update) => ({ exec: async () => ({ matchedCount: apply(filter, update) ? 1 : 0 }) }),
  } };
  delete require.cache[controllerPath];
  try { await action(require('../controllers/project')); }
  finally {
    if (oldModel) require.cache[modelPath] = oldModel; else delete require.cache[modelPath];
    if (oldController) require.cache[controllerPath] = oldController; else delete require.cache[controllerPath];
  }
}

test('[UI-04.1] fresh status reads recover persisted image and video progress without WebSocket events', async () => {
  const project = fixture();
  await withController(project, async controller => {
    await controller.recordProcessingProgress('owner', 'project', 7, { messageId: 'image-step-1' });
    await controller.recordProcessingProgress('owner', 'project', 7, { videoId: 'video', percent: 50 });
    const recovered = processingStatus(JSON.parse(JSON.stringify(project)), true);
    assert.equal(recovered.progress, 50);
    assert.equal(recovered.token, 7);
    assert.equal(recovered.canCancel, true);
    assert.equal(recovered.projectVersion, 4);
  });
});

test('[UI-04.1] repeated and out-of-order progress cannot advance twice or move backwards', async () => {
  const project = fixture();
  await withController(project, async controller => {
    for (let n = 0; n < 2; n++) await controller.recordProcessingProgress('owner', 'project', 7, { messageId: 'step' });
    await controller.recordProcessingProgress('owner', 'project', 7, { videoId: 'video', percent: 75 });
    await controller.recordProcessingProgress('owner', 'project', 7, { videoId: 'video', percent: 10 });
    await controller.recordProcessingProgress('owner', 'project', 6, { videoId: 'video', percent: 100 });
    assert.deepEqual(project.processingState.completedMessages, ['step']);
    assert.equal(project.processingState.videoProgress.video, 75);
    assert.equal(processingStatus(project).progress, 58);
  });
});

test('[UI-04.1] progress remains below 100 until the result is committed', async () => {
  const project = fixture();
  project.processingState.completedMessages = ['step-1', 'step-2'];
  project.processingState.videoProgress.video = 100;
  assert.equal(processingStatus(project, true).progress, 99);
  await withController(project, async controller => {
    assert.ok(await controller.commitRunIfActive('owner', 'project', 7, [], true));
  });
  assert.equal(processingStatus(project, true).progress, 100);
  assert.equal(processingStatus(project, true).status, 'completed');
  assert.equal(processingStatus(project, true).canCancel, false);
});

test('[UI-04.1] cancellation survives a fresh read and rejects late events from the old run', async () => {
  const project = fixture();
  await withController(project, async controller => {
    const cancelled = { ...project, activeToken: 8 };
    const run = { ...project.processingState, status: 'cancelled' };
    assert.ok(await controller.updateIfVersion('owner', 'project', cancelled, 4,
      { activeToken: 7, requireProcessing: true, processingState: run }));
    await controller.recordProcessingProgress('owner', 'project', 7, { videoId: 'video', percent: 100 });
    assert.equal(await controller.commitRunIfActive('owner', 'project', 7, [], true), null);
    const recovered = processingStatus(structuredClone(project), true);
    assert.equal(recovered.status, 'cancelled');
    assert.equal(recovered.canCancel, false);
    assert.equal(project.processingState.videoProgress.video, 0);
  });
});

test('[UI-04.1] stale cancellation cannot cancel a newer or already completed execution', async () => {
  const project = fixture();
  await withController(project, async controller => {
    const options = { activeToken: 6, requireProcessing: true,
      processingState: { ...project.processingState, status: 'cancelled' } };
    assert.equal(await controller.updateIfVersion('owner', 'project', project, 4, options), null);
    await controller.commitRunIfActive('owner', 'project', 7, [], true);
    assert.equal(await controller.updateIfVersion('owner', 'project', project, 4,
      { ...options, activeToken: 7 }), null);
    assert.equal(project.processingState.status, 'completed');
  });
});

test('[UI-04.1] failures survive reload and cannot become completed through late success', async () => {
  const project = fixture();
  await withController(project, async controller => {
    await controller.failProcessing('owner', 'project', 7, 'Storage unavailable');
    assert.equal(await controller.commitRunIfActive('owner', 'project', 7, [], true), null);
    await controller.recordProcessingProgress('owner', 'project', 7, { videoId: 'video', percent: 100 });
  });
  const recovered = processingStatus(structuredClone(project), true);
  assert.equal(recovered.status, 'failed');
  assert.equal(recovered.error, 'Storage unavailable');
  assert.equal(recovered.canCancel, false);
});

test('[UI-04.1] ordinary edits do not overwrite persisted worker progress', async () => {
  const project = fixture(), stale = structuredClone(project);
  await withController(project, async controller => {
    await controller.recordProcessingProgress('owner', 'project', 7, { videoId: 'video', percent: 60 });
    await controller.updateIfVersion('owner', 'project', { ...stale, name: 'Renamed' }, 4);
  });
  assert.equal(project.processingState.videoProgress.video, 60);
});

async function statusRequest(project, caller, permission) {
  const response = { code: 200, headers: {}, status(code) { this.code = code; return this; },
    set(key, value) { this.headers[key] = value; }, json(value) { this.body = value; },
    jsonp(value) { this.body = value; } };
  await createStatusHandler({ getOne: async () => project }, () => caller)(
    { params: { user: 'owner', project: 'project' }, sharedPermission: permission }, response);
  return response;
}

test('[UI-04.1] status is uncached and respects owner and project share permissions', async () => {
  const project = fixture();
  const owner = await statusRequest(project, 'owner');
  assert.equal(owner.headers['Cache-Control'], 'no-store');
  assert.equal(owner.body.canCancel, true);
  assert.equal((await statusRequest(project, 'reader', 'read')).body.canCancel, false);
  assert.equal((await statusRequest(project, 'editor', 'edit')).body.canCancel, true);
  assert.equal((await statusRequest(project, 'stranger')).code, 403);
  assert.equal((await statusRequest(null, 'owner')).code, 404);
});

test('[UI-04.1] projects without a run report idle rather than inventing active progress', () => {
  assert.deepEqual(processingStatus({ version: 3 }, true), {
    status: 'idle', token: null, progress: 0, canCancel: false, projectVersion: 3,
  });
});

test('[UI-04.1] unavailable status returns an error rather than pretending the run is idle', async () => {
  let status, body;
  const response = { status(code) { status = code; return this; }, jsonp(value) { body = value; } };
  await createStatusHandler({ getOne: async () => { throw new Error('database offline'); } }, () => 'owner')(
    { params: { user: 'owner', project: 'project' } }, response);
  assert.equal(status, 500);
  assert.equal(body, 'Unable to read processing status');
});

test('[UI-04.1] active runs preserve navigation and cancellation but reject destructive pipeline edits', async () => {
  const controllerPath = require.resolve('../controllers/project');
  const middlewarePath = require.resolve('../middleware/projectVersion');
  const oldController = require.cache[controllerPath], oldMiddleware = require.cache[middlewarePath];
  require.cache[controllerPath] = { id: controllerPath, filename: controllerPath, loaded: true,
    exports: { getOne: async () => fixture() } };
  delete require.cache[middlewarePath];
  try {
    const { requireProjectVersion } = require('../middleware/projectVersion');
    for (const path of ['/owner/project/tool/tool-id', '/owner/project/clear', '/owner/project/img',
      '/owner/project/video', '/owner/project/reorder', '/owner/project/assistant/apply']) {
      let status, called = false;
      await requireProjectVersion({ path, headers: { 'x-project-version': '4' },
        params: { user: 'owner', project: 'project' } },
      { status(code) { status = code; return this; }, jsonp() {} }, () => { called = true; });
      assert.equal(status, 409, path);
      assert.equal(called, false, path);
    }
    let called = false;
    await requireProjectVersion({ path: '/owner/project/process', headers: { 'x-project-version': '4' },
      params: { user: 'owner', project: 'project' } }, {}, () => { called = true; });
    assert.equal(called, true);
  } finally {
    if (oldController) require.cache[controllerPath] = oldController; else delete require.cache[controllerPath];
    if (oldMiddleware) require.cache[middlewarePath] = oldMiddleware; else delete require.cache[middlewarePath];
  }
});

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  imageTools,
  videoPipeline,
  videoStages,
  videoOps,
  unsupportedVideoTools,
  resolveVideoWorkerTool,
} = require('../utils/video');

test('captions apply to all videos, while images skip them and trim stays targeted', () => {
  const project = {
    imgs: [{ _id: 'a', media_type: 'video' }, { _id: 'b', media_type: 'video' }, { _id: 'c', media_type: 'image' }],
    tools: [
      { position: 2, procedure: 'subtitles', params: {} },
      { position: 0, procedure: 'brightness', params: { brightness: 0.5 } },
      { position: 1, procedure: 'trim', params: { imgId: 'a', start: 0, end: 2 } },
    ],
  };
  assert.deepEqual(imageTools(project).map(t => t.procedure), ['brightness']);
  assert.deepEqual(videoPipeline(project, 'a').map(t => t.procedure), ['brightness', 'trim', 'subtitles']);
  assert.deepEqual(videoPipeline(project, 'b').map(t => t.procedure), ['brightness', 'subtitles']);
  assert.equal(videoOps(project), 5);
  assert.deepEqual(unsupportedVideoTools(project), []);
  project.tools = [project.tools[0]];
  assert.deepEqual(imageTools(project), []);
  assert.equal(videoOps(project), 2);
});

test('splits mixed video pipelines into ordered worker stages', () => {
  const project = {
    tools: [
      { position: 0, procedure: 'brightness', params: { brightness: 0.5 } },
      { position: 1, procedure: 'subtitles', params: {} },
      { position: 2, procedure: 'extract_frames', params: { mode: 'count', count: 5, format: 'png' } },
    ],
  };
  assert.deepEqual(videoStages(project, 'video').map((stage) => stage.tool), [
    'video_effects',
    'video_subtitles',
    'video_frames',
  ]);

  project.tools = [
    { position: 0, procedure: 'brightness', params: {} },
    { position: 1, procedure: 'contrast', params: {} },
  ];
  assert.deepEqual(videoStages(project, 'video'), [{
    tool: 'video_effects',
    tools: [
      { procedure: 'brightness', params: {} },
      { procedure: 'contrast', params: {} },
    ],
  }]);

  project.tools = [
    { position: 0, procedure: 'subtitles', params: {} },
    { position: 1, procedure: 'brightness', params: {} },
    { position: 2, procedure: 'subtitles', params: {} },
  ];
  assert.deepEqual(videoStages(project, 'video').map((stage) => stage.tool), [
    'video_subtitles',
    'video_effects',
    'video_subtitles',
  ]);
  assert.deepEqual(videoStages({ tools: [] }, 'video'), []);
});

test('keeps the legacy worker resolver compatible for existing callers', () => {
  assert.equal(resolveVideoWorkerTool([{ procedure: 'brightness' }, { procedure: 'trim' }]), 'video_effects');
  assert.equal(resolveVideoWorkerTool([{ procedure: 'brightness' }, { procedure: 'subtitles' }]), 'video_subtitles');
  assert.equal(resolveVideoWorkerTool([{ procedure: 'brightness' }, { procedure: 'extract_frames' }]), 'video_frames');
  assert.equal(resolveVideoWorkerTool([]), 'video_effects');
});

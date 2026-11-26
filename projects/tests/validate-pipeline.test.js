const test = require('node:test');
const assert = require('node:assert/strict');
const {
  PER_VIDEO_TOOLS,
  validatePipeline,
  videoToolsError,
} = require('../utils/video');

const IMAGE = { _id: 'i1', media_type: 'image' };
const VIDEO = { _id: 'v1', media_type: 'video' };
const EXTRACT = { procedure: 'extract_frames', params: { mode: 'count', count: 6, format: 'png' } };

// Builds a project; tools are given in pipeline order
const project = (imgs, ...tools) => ({
  imgs,
  tools: tools.map((t, position) => ({ position, params: {}, ...(typeof t === 'string' ? { procedure: t } : t) })),
});

test('a pipeline without tools is rejected', () => {
  assert.equal(validatePipeline(project([IMAGE])), 'No tools selected');
});

test('image tools on a project with only images are valid', () => {
  assert.equal(validatePipeline(project([IMAGE], 'brightness', 'watermark', 'bg_remove_ai')), null);
});

test('image-only tools are rejected as soon as the project has a video', () => {
  assert.equal(
    validatePipeline(project([IMAGE, VIDEO], 'brightness', 'watermark')),
    'Effects not available for video: watermark'
  );
  // repeated tools are listed once
  assert.equal(
    validatePipeline(project([VIDEO], 'watermark', 'bg_remove_ai', 'watermark')),
    'Effects not available for video: watermark, bg_remove_ai'
  );
});

test('effects that work on video, and video-only ones, are valid with videos', () => {
  const ok = project([IMAGE, VIDEO], 'brightness', 'rotate', { procedure: 'trim', params: { imgId: 'v1', start: 0, end: 2 } }, 'speed', 'subtitles', EXTRACT);
  assert.equal(validatePipeline(ok), null);
});

test('a pipeline made only of video effects needs at least one video', () => {
  assert.equal(
    validatePipeline(project([IMAGE], 'trim', 'speed')),
    'The pipeline only has video effects and the project has no videos'
  );
  assert.equal(
    validatePipeline(project([], 'subtitles')),
    'The pipeline only has video effects and the project has no videos'
  );
  // with an image effect the video-only steps are just skipped for images
  assert.equal(validatePipeline(project([IMAGE], 'brightness', 'trim')), null);
});

test('frame extraction must be the last tool and appear only once', () => {
  assert.equal(
    validatePipeline(project([VIDEO], EXTRACT, 'brightness')),
    'Frame extraction must be the last tool in the pipeline'
  );
  assert.equal(
    validatePipeline(project([VIDEO], EXTRACT, EXTRACT)),
    'Only one frame extraction tool is allowed'
  );
});

test('frame extraction problems are reported before the video ones (same order as POST /process)', () => {
  assert.equal(
    validatePipeline(project([VIDEO], EXTRACT, 'watermark')),
    'Frame extraction must be the last tool in the pipeline'
  );
});

test('videoToolsError is null when every effect works on video', () => {
  assert.equal(videoToolsError(project([VIDEO], 'brightness', 'trim', EXTRACT)), null);
  assert.equal(videoToolsError(project([VIDEO], 'upgrade_ai')), 'Effects not available for video: upgrade_ai');
});

test('trim and speed are the per-video tools', () => {
  assert.deepEqual([...PER_VIDEO_TOOLS].sort(), ['speed', 'trim']);
});

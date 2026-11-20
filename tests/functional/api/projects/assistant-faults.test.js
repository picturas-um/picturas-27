const { test } = require('node:test');
const assert = require('node:assert/strict');
const { failedPreview } = require('../../../helpers/assistant-faults');

// Run the actual Express handler with failing storage adapters in a separate
// process. This never changes adapters in the running projects service.
test('[ASSIST-02] storage upload failure returns usable suggestions without a preview', () => {
  const result = failedPreview('upload');
  assert.equal(result.status, 200);
  assert.ok(result.body.suggestions.length > 0);
  assert.ok(result.body.suggestions.every(s => s.previewUrl === null && s.tools.length > 0));
  assert.equal(result.uploaded, 0);
});



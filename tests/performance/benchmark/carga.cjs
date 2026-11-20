const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const { setTimeout: sleep } = require('node:timers/promises');
const { request, success, project, fixture } = require('../../helpers/live');

const scenario = process.argv[2];
const file = process.argv[3];
const events = fs.createWriteStream(file);
const emit = data => events.write(JSON.stringify({ at: Date.now(), ...data }) + '\n');
const video = process.env.PERF_VIDEO || fixture('clip.mp4');
const filename = path.basename(video);
if (!/^[a-zA-Z0-9_.-]+\.mp4$/i.test(filename)) throw new Error('Expected an MP4 filename');
const pollMs = 200;
const cutTimeoutMs = 30000;
const auditTimeoutMs = 180000;
const recoverySeconds = Number(process.env.PERF_RECOVERY_SECONDS || 45);
if (!Number.isInteger(recoverySeconds) || recoverySeconds < 1) throw new Error("Invalid recovery duration");
const workload = {
  warmup: [{ name: 'warmup', seconds: 4, rate: 1, users: 4 }],
  low: [{ name: 'low', seconds: 6, rate: 0.5, users: 1 }],
  mixed: [{ name: 'mixed', seconds: 12, rate: 2, users: 12 }],
  peak: [
    { name: 'normal', seconds: 6, rate: 2, users: 12 },
    { name: 'peak', seconds: 6, rate: 8, users: 48 },
    { name: 'recovery', seconds: recoverySeconds, rate: 2, users: 12 },
  ],
};
let job = 0;
const resultIds = new Set();
const acceptedJobs = [];

async function run(phase, deadline) {
  const id = ++job;
  let accepted = false;
  let stage = 'setup';
  let projectId;
  const elapsed = start => performance.now() - start;
  const time = async (op, action) => {
    stage = op;
    const start = performance.now();
    try {
      const response = await action();
      emit({ phase, id, op, ms: elapsed(start), status: response.status });
      return success(response);
    } catch (error) {
      emit({ phase, id, op: 'operation_error', stage, error: error.message });
      throw error;
    }
  };
  try {
    const p = await project();
    projectId = p.id;
    const current = await p.get();
    const headers = { 'X-Project-Version': String(current.version) };
    const boundary = 'picturas-baseline';
    const raw = Buffer.concat([
      Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="video"; filename="${filename}"\r\nContent-Type: video/mp4\r\n\r\n`),
      fs.readFileSync(video),
      Buffer.from(`\r\n--${boundary}--\r\n`),
    ]);
    const options = { token: p.user.token };
    await time('upload', () => request('POST', p.route + '/video', {
      ...options, raw, headers: { ...headers, 'Content-Type': `multipart/form-data; boundary=${boundary}` },
    }));
    stage = 'pipeline';
    const source = (await p.get()).imgs[0]._id;
    await p.tools([{ procedure: 'trim', params: { imgId: source, start: 0, end: 2 } }]);
    const version = (await p.get()).version;
    const cutStart = performance.now();
    await time('cut_api', () => request('POST', p.route + '/process', {
      ...options, body: {}, headers: { 'X-Project-Version': String(version) },
    }));
    accepted = true;
    acceptedJobs.push({ p, phase, id, source });
    emit({ phase, id, projectId, op: 'accepted' });
    let results;
    do {
      results = await time('status', () => request('GET', p.route + '/process/url', options));
      if (results.imgs.length) break;
      if (elapsed(cutStart) >= cutTimeoutMs) throw new Error('Cut timed out');
      await sleep(pollMs);
    } while (true);
    emit({ phase, id, op: 'cut_total', ms: elapsed(cutStart) });
    stage = 'integrity';
    const [output] = results.imgs;
    if (results.imgs.length !== 1 || results.texts.length || output.og_img_id !== source ||
        !output.result_id || resultIds.has(output.result_id)) throw new Error('Unexpected or duplicate result');
    resultIds.add(output.result_id);
    const url = new URL(output.url, process.env.TEST_BASE_URL);
    if (url.origin !== new URL(process.env.TEST_BASE_URL).origin) throw new Error('Download URL outside isolated stack');
    await time('download', () => request('GET', url.href));
    emit({ phase, id, projectId, op: 'completed', afterArrivalPhase: Date.now() > deadline });
    return { resultId: output.result_id, id };
  } catch (error) {
    emit({ phase, id, projectId, op: 'failed', accepted, stage, timeout: /timed out|timeout/i.test(error.message), error: error.message });
    return null;
  }
}

async function main() {
  const checks = [];
  for (const phase of workload[scenario]) {
    const pending = new Set();
    const start = Date.now();
    const deadline = start + phase.seconds * 1000;
    emit({ op: 'phase', ...phase });
    for (let index = 0; index < phase.seconds * phase.rate; index++) {
      await sleep(Math.max(0, start + index * 1000 / phase.rate - Date.now()));
      if (pending.size >= phase.users) {
        emit({ phase: phase.name, op: 'shed' });
        continue;
      }
      const task = run(phase.name, deadline);
      pending.add(task);
      checks.push(task);
      task.finally(() => pending.delete(task));
    }
    await sleep(Math.max(0, deadline - Date.now()));
  }
  const results = await Promise.all(checks);
  if (scenario === 'peak') {
    const observed = new Map(results.filter(Boolean).map(result => [result.id, result.resultId]));
    const finalIds = new Set();
    const pending = new Set(acceptedJobs);
    const end = Date.now() + auditTimeoutMs;
    emit({ op: 'audit_start', timeoutMs: auditTimeoutMs });
    do {
      for (const job of pending) {
        const { p, phase, id, source } = job;
        if (Date.now() >= end) {
          emit({ phase, id, op: 'audit', ok: false, error: 'Audit deadline reached' });
          pending.delete(job);
          continue;
        }
        try {
          const body = success(await request('GET', p.route + '/process/url', { token: p.user.token }));
          const result = body.imgs[0];
          if (!result && body.texts.length === 0 && Date.now() < end) continue;
          const duplicate = Boolean(result && finalIds.has(result.result_id));
          if (result) finalIds.add(result.result_id);
          const resultId = observed.get(id);
          const ok = body.imgs.length === 1 && body.texts.length === 0 &&
            result.og_img_id === source && Boolean(result.result_id) && !duplicate &&
            (!resultId || result.result_id === resultId);
          emit({ phase, id, op: 'audit', ok, duplicate, resultCount: body.imgs.length });
        } catch (error) {
          if (Date.now() < end) continue;
          emit({ phase, id, op: 'audit', ok: false, error: error.message });
        }
        pending.delete(job);
      }
      if (pending.size) await sleep(1000);
    } while (pending.size);
  }
}
main().catch(error => { emit({ op: 'fatal', error: error.message }); process.exitCode = 1; })
  .finally(() => events.end());

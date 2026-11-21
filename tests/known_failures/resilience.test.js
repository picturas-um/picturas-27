const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { request, success, until, fixtures, account, project, db } = require('../helpers/live');

function docker(...args) {
  return execFileSync('docker', args, { encoding: 'utf8', timeout: 90000, stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}
function image(service) { return docker('compose', 'images', '-q', service).split('\n')[0]; }
function sandbox(t) {
  const name = 'picturas-regression-' + randomUUID().slice(0, 8);
  docker('network', 'create', name);
  const containers = [];
  t.after(() => {
    for (const id of containers.reverse()) { try { docker('rm', '-f', id); } catch {} }
    docker('network', 'rm', name);
  });
  return {
    run(label, img, args = [], command = []) {
      const container = `${name}-${label}`;
      docker('run', '-d', '--name', container, '--network', name, '--network-alias', label, ...args, img, ...command);
      containers.push(container); return container;
    },
  };
}



test('[RUN-03] isolated video worker resumes processing after broker restart', { timeout: 240000 }, async t => {
  const isolated = sandbox(t), dir = fs.mkdtempSync(path.join(os.tmpdir(), 'picturas-resilience-'));
  fs.chmodSync(dir, 0o777); t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const broker = isolated.run('broker', image('rabbitmq'), ['-p', '127.0.0.1::15672']);
  const address = docker('port', broker, '15672/tcp');
  const base = `http://${address}/api`;
  const auth = { Authorization: 'Basic ' + Buffer.from('user:password').toString('base64') };
  const api = (method, route, body) => request(method, base + route, { headers: auth, body });
  await until(async () => { try { return (await api('GET', '/overview')).status === 200; } catch { return false; } }, 90000);
  isolated.run('worker', image('video_effects_tool'), ['--restart', 'on-failure', '-e', 'RABBITMQ_HOST=broker', '-e', 'VIDEO_QUEUE=video_queue', '-v', `${fixtures}:/fixtures:ro`, '-v', `${dir}:/out`]);
  const consumersReady = async () => (await api('GET', '/queues/%2F/video_queue')).data.consumers > 0;
  await until(consumersReady, 60000);
  async function job(name) {
    const message = { messageId: name, timestamp: new Date().toISOString(), procedure: 'video', parameters: {
      inputImageURI: '/fixtures/videos/clip.mp4', outputImageURI: `/out/${name}.mp4`, tools: [{ procedure: 'brightness', params: { brightness: 0.5 } }],
    } };
    const sent = success(await api('POST', '/exchanges/%2F/picturas/publish', { properties: {}, routing_key: 'video_queue', payload: JSON.stringify(message), payload_encoding: 'string' }));
    assert.equal(sent.routed, true);
    const reply = await until(async () => {
      const messages = success(await api('POST', '/queues/%2F/project_queue/get', { count: 10, ackmode: 'ack_requeue_false', encoding: 'auto' }));
      return messages.map(x => JSON.parse(x.payload)).find(x => x.correlationId === name);
    }, 60000);
    assert.equal(reply.status, 'success'); assert.ok(fs.statSync(path.join(dir, `${name}.mp4`)).size > 0);
  }
  await job('before'); docker('restart', broker);
  await until(async () => { try { return await consumersReady(); } catch { return false; } }, 90000);
  await job('after');
});

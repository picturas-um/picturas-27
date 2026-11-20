const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { request, success, until, fixtures, account, project, db } = require('../../helpers/live');

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



test('[DATA-02,OPS-01] backup restores all three databases and an isolated Mongo restart preserves data', { timeout: 180000 }, async t => {
  const isolated = sandbox(t), mongoImage = image('users_mongoDB');
  const source = isolated.run('source', mongoImage), target = isolated.run('target', mongoImage);
  async function ready(container) {
    await until(async () => { try { return docker('exec', container, 'mongo', '--quiet', '--eval', 'db.adminCommand({ping:1}).ok') === '1'; } catch { return false; } }, 60000);
  }
  await ready(source); await ready(target);
  const a = await account(), p = await project(a);
  const user = db('users', a.id), proj = db('projects', a.id, 'findOne', null, 'projects');
  const seed = `db.getSiblingDB('user').users.insertOne(${JSON.stringify(user)});db.getSiblingDB('project').projects.insertOne(${JSON.stringify(proj)});db.getSiblingDB('subscription').subscriptions.insertOne({user_id:'${a.id}',status:'active'});`;
  docker('exec', source, 'mongo', '--quiet', '--eval', seed);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'picturas-backup-')); t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  for (const database of ['user', 'project', 'subscription']) {
    docker('exec', source, 'mongodump', '--db', database, `--archive=/tmp/${database}.gz`, '--gzip');
    docker('cp', `${source}:/tmp/${database}.gz`, path.join(dir, database + '.gz'));
    docker('cp', path.join(dir, database + '.gz'), `${target}:/tmp/${database}.gz`);
    docker('exec', target, 'mongorestore', `--archive=/tmp/${database}.gz`, '--gzip');
  }
  docker('restart', target); await ready(target);
  const verify = `print(JSON.stringify({user:db.getSiblingDB('user').users.findOne({_id:'${a.id}'}),project:db.getSiblingDB('project').projects.findOne({_id:'${p.id}'}),subscription:db.getSiblingDB('subscription').subscriptions.findOne({user_id:'${a.id}'})}))`;
  const restored = JSON.parse(docker('exec', target, 'mongo', '--quiet', '--eval', verify));
  assert.equal(restored.user.email_encrypted, user.email_encrypted);
  assert.equal(restored.project.user_id, a.id);
  assert.equal(restored.subscription.status, 'active');
});

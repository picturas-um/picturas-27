const { test } = require('node:test');
const assert = require('node:assert/strict');
const { request, success, account, project, db } = require('../../../helpers/live');

test('[PLAN-01] free quota allows five operations and refuses the sixth', async () => {
  const a = await account();
  for (let i = 0; i < 5; i++) success(await request('GET', `https://localhost:10001/${a.id}/process/1`));
  assert.ok((await request('GET', `https://localhost:10001/${a.id}/process/1`)).status >= 400);
  const state = db('users', a.id);
  assert.equal(state.operations.reduce((n, x) => n + x.processed, 0), 5);
});

test('[PLAN-01] anonymous cannot reserve operations and premium can exceed five', async () => {
  const anon = await account('anonymous'), premium = await account();
  db('users', premium.id, 'updateOne', { type: 'premium' });
  assert.ok((await request('GET', `https://localhost:10001/${anon.id}/process/1`)).status >= 400);
  success(await request('GET', `https://localhost:10001/${premium.id}/process/6`));
});

test('[PLAN-04] a previous days quota does not prevent operations today', async () => {
  const a = await account();
  // The data setup uses Mongo's date type, not a string in the operations array.
  const { dockerNode } = require('../../../helpers/live');
  dockerNode('users', `const m=require('mongoose');(async()=>{await m.connect('mongodb://users_mongoDB:27019/user');await m.connection.db.collection('users').updateOne({_id:new m.Types.ObjectId(process.argv[1])},{$set:{operations:[{day:new Date(Date.now()-86400000),processed:5}]}});await m.disconnect()})()`, [a.id]);
  success(await request('GET', `https://localhost:10001/${a.id}/process/1`));
  const stored = db('users', a.id);
  assert.equal(stored.operations.length, 2);
  assert.equal(stored.operations.reduce((n, x) => n + x.processed, 0), 6);
});

test('[CONC-01] concurrent reservations cannot spend the last operation twice', async () => {
  const a = await account();
  success(await request('GET', `https://localhost:10001/${a.id}/process/4`));
  const responses = await Promise.all(Array.from({ length: 8 }, () => request('GET', `https://localhost:10001/${a.id}/process/1`)));
  assert.equal(responses.filter(r => r.status === 200).length, 1, 'Exactly one reservation may succeed');
  assert.equal(db('users', a.id).operations.reduce((n, x) => n + x.processed, 0), 5);
});

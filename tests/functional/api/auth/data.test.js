const { test } = require('node:test');
const assert = require('node:assert/strict');
const { request, success, account, project, db } = require('../../../helpers/live');

const card = { cardHolderName: 'Regression Test', cardNumber: '4242424242424242', expiryMonth: '12', expiryYear: '30', cvc: 123 };
async function subscribe(a) {
  return success(await request('POST', '/api-gateway/subscriptions/', { token: a.token, body: { subscription: { user_id: a.id, interval: 1 }, card } }));
}

test('[DATA-01] persisted identity is encrypted and password is hashed', async () => {
  const a = await account(), stored = db('users', a.id);
  assert.notEqual(stored.email_encrypted, a.email);
  assert.ok(stored.email_encrypted && stored.email_hash);
  assert.equal(stored.email, undefined);
  assert.notEqual(stored.password_hash, a.password);
  assert.match(stored.password_hash, /^\$2[aby]\$/);
});

test('[DATA-01] a fresh service process reads encrypted card data without plaintext persistence', async () => {
  const a = await account(); await subscribe(a);
  const { dockerNode } = require('../../../helpers/live');
  const result = JSON.parse(dockerNode('subscriptions', `const m=require('mongoose');const Card=require('./models/card');(async()=>{await m.connect('mongodb://subscriptions_mongoDB/subscription');const sub=await m.connection.db.collection('subscriptions').findOne({user_id:new m.Types.ObjectId(process.argv[1])});const card=await Card.findOne({subscriptionId:sub._id});const raw=card.toObject();console.log(JSON.stringify({encrypted:raw.cardToken!==process.argv[2],readable:card.getDecryptedCardToken()===process.argv[2],last4:raw.last4,hasCvc:'cvc' in raw}));await m.disconnect()})()`, [a.id, card.cardNumber]).trim());
  assert.deepEqual(result, { encrypted: true, readable: true, last4: '4242', hasCvc: false });
});

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { request, success, account, project, db } = require('../../../helpers/live');

const card = { cardHolderName: 'Regression Test', cardNumber: '4242424242424242', expiryMonth: '12', expiryYear: '30', cvc: 123 };
async function subscribe(a) {
  return success(await request('POST', '/api-gateway/subscriptions/', { token: a.token, body: { subscription: { user_id: a.id, interval: 1 }, card } }));
}

test('[PLAN-03.1] subscription changes free account to premium', async () => {
  const a = await account(); await subscribe(a);
  assert.equal(success(await request('GET', `/api-gateway/users/${a.id}`, { token: a.token })).type, 'premium');
  assert.ok(success(await request('GET', `/api-gateway/subscriptions/${a.id}/status`, { token: a.token })));
});

test('[PLAN-03.2] subscription card can be updated and read with masked details', async () => {
  const a = await account(); await subscribe(a);
  const result = success(await request('PUT', `/api-gateway/subscriptions/${a.id}/card`, { token: a.token, body: { ...card, cardHolderName: 'Updated Holder' } }));
  assert.equal(result.cardHolderName, 'Updated Holder');
  assert.equal(JSON.stringify(result).includes(card.cardNumber), false, 'Full card number must not be returned');
  assert.equal(result.cvc, undefined);
});

test('[PLAN-03.3] cancellation returns the account to free', async () => {
  const a = await account(); await subscribe(a);
  success(await request('PUT', `/api-gateway/subscriptions/${a.id}/cancel`, { token: a.token, body: {} }));
  assert.equal(success(await request('GET', `/api-gateway/users/${a.id}`, { token: a.token })).type, 'free');
});

const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { request, success, account, project, fixtures, db, dockerNode } = require('../../../helpers/live');

test('[PLAN-04] coverage: quota changes at the UTC day boundary without double counting', () => {
  const output = dockerNode('users', `
    const User=require('./controllers/user');const router=require('./routes/users');
    const OriginalDate=Date;let clock='2026-11-06T23:59:59Z';
    global.Date=class extends OriginalDate{constructor(...a){super(...(a.length?a:[clock]))}static now(){return new OriginalDate(clock).getTime()}};
    let state={type:'free',operations:[{day:new Date(2026,10,6),processed:5}]};
    User.getOne=async()=>state;User.update=async(_,value)=>{state=value};
    const handler=router.stack.find(x=>x.route?.path==='/:user/process/:advanced_tools'&&x.route.methods.get).route.stack.at(-1).handle;
    const call=()=>new Promise(resolve=>{let status=200;handler({params:{user:'test',advanced_tools:'1'}},{status(s){status=s;return this},jsonp(body){resolve({status,body})}})});
    (async()=>{const before=await call();clock='2026-11-07T00:00:00Z';const after=await call();console.log(JSON.stringify({before:before.status,after:after.status,operations:state.operations.map(x=>x.processed)}))})()
  `);
  const result = JSON.parse(output.trim().split('\n').at(-1));
  assert.ok(result.before >= 400); assert.equal(result.after, 200); assert.deepEqual(result.operations, [5, 1]);
});

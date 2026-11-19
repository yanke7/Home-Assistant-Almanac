const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
let Card;const source=fs.readFileSync(path.join(__dirname,'../almanac-sky-card.js'),'utf8');
vm.runInNewContext(source,{Date,window:{},HTMLElement:class{attachShadow(){}},customElements:{get(){},define(n,c){Card=c;}}});
(async()=>{
 const c=new Card();c.isConnected=true;c.draw=()=>{};c.init=()=>{};
 const snap={now:Date.now(),location:{latitude:52.13,longitude:-106.67,time_zone:'America/Regina'},chart_key:"home-day",days:[{d0:123,end:456}],sun:{alt:1},moon:{alt:2},illumination:{f:.5}};
 let calls=0;c._hass={config:snap.location,callWS:async()=>{calls++;return snap;}};
 await c.syncBackend();assert.equal(c.backend.sun.alt,1);assert.equal(c.cache.get(123).end,456);
 await c.syncBackend();assert.equal(calls,1,'avoid repeated requests');
 c.lastFetch=0;c._hass.callWS=async()=>{throw Error('offline')};await c.syncBackend();assert.equal(c.backend,null,'do not display stale live readings');
 c.lastFetch=0;c._hass.callWS=async()=>snap;await c.syncBackend();assert.equal(c.backend.sun.alt,1,'recover after reconnect');
 c.lastFetch=0;c._hass.callWS=async request=>{assert.equal(request.chart_key,'home-day');const {days,...light}=snap;return light;};await c.syncBackend();assert.equal(c.cache.get(123).end,456,'keep charts with lightweight updates');
 c.lastFetch=0;c._hass.callWS=async()=>({...snap,days:Array.from({length:10},(_,i)=>({d0:i,end:i+1}))});await c.syncBackend();assert.equal(c.cache.size,7,'bound backend chart cache');
 c.lastFetch=0;c._hass.callWS=async()=>snap;
 c.lastFetch=0;c._hass.config={...snap.location,latitude:0};await c.syncBackend();assert.equal(c.backend,null,'reject snapshots for previous location');
 console.log('Backend snapshot, throttling, failure and recovery checks passed');
})().catch(e=>{console.error(e);process.exitCode=1});

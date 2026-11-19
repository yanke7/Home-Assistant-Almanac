const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let Card, now;
class Clock extends Date { static now(){return now;} }
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'almanac-sky-card.js'),'utf8'),{
  Date:Clock,window:{},HTMLElement:class {attachShadow(){}},
  getComputedStyle(){return {position:'relative'};},ResizeObserver:class {observe(){} disconnect(){}},
  customElements:{get(){},define(name,card){Card=card;}}
});
for(const [zone,start,end] of [
  ['America/Chicago','2026-03-08T06:00Z','2026-03-09T05:00Z'],
  ['America/Chicago','2026-11-01T05:00Z','2026-11-02T06:00Z'],
  ['America/Chicago','2026-01-04T06:00Z','2026-01-05T06:00Z'],
  ['Asia/Kolkata','2026-03-07T18:30Z','2026-03-08T18:30Z']
]){
  const first=Date.parse(start),last=Date.parse(end),card=new Card(),elements={};
  function element(id){
    return elements[id]??={events:{},addEventListener(k,f){this.events[k]=f;},
      setPointerCapture(){},getBoundingClientRect(){return {left:0,width:100};}};
  }
  now=first+12*3600000;
  Object.assign(card,{isConnected:true,config:{},shadowRoot:{getElementById:element},draw(){}});
  card.hass={config:{latitude:41,longitude:-88,time_zone:zone}};
  for(const instant of [first,now,last-1])assert.equal(card.dayStart(instant),first);
  assert.equal(card.dayStart(last),last);
  assert.equal(card.nextStart(first),last);
  assert.equal(card.dayTag(last,first),'tomorrow');
  const d=card.day(first),chart=element('chart');
  assert.equal(d.t[0],first);
  assert.equal(d.t.at(-1),last);
  assert.equal(d.t.length,1+(last-first)/120000);
  card.W=720;
  card.plot(d,last,{alt:4},{alt:6});
  assert.match(element('plot').innerHTML,/circle cx="720.0"/);
  assert.doesNotMatch(element('plot').innerHTML,/NaN|undefined/);
  for(const [x,key,expected] of [[0,'ArrowLeft',first],[100,'PageUp',last]]){
    chart.events.pointerdown({clientX:x,pointerId:1});
    assert.equal(card.scrub,expected);
    chart.events.keydown({key,preventDefault(){}});
    assert.equal(card.scrub,expected);
  }
  chart.events.keydown({key:'Escape'});
  assert.equal(card.scrub,null);
  card.cycle(now,first);
  const titles=[...element('cycle').innerHTML.matchAll(/ title="([^:]+):/g)].map(match=>match[1]);
  assert.equal(new Set(titles).size,28);
}
console.log('Local day, chart and selection checks passed');

const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
let Card;const at=Date.parse(process.argv[2]);class Clock extends Date{static now(){return at}}
let source=fs.readFileSync(path.join(__dirname,'../almanac-sky-card.js'),'utf8');
source=source.replace("if (!customElements.get('almanac-sky-card'))", "window.astro={sunAt,moonAt,illum}; if (!customElements.get('almanac-sky-card'))");
const window={};vm.runInNewContext(source,{Date:Clock,window,HTMLElement:class{attachShadow(){}},customElements:{get(){},define(n,c){Card=c;}}});
const lat=+process.argv[3],lon=+process.argv[4],tz=process.argv[5];const c=new Card();
c.lat=lat;c.lon=lon;c.fP=new Intl.DateTimeFormat('en-US',{timeZone:tz,year:'numeric',month:'numeric',day:'numeric'});
console.log(JSON.stringify({sun:window.astro.sunAt(at,lat,lon),moon:window.astro.moonAt(at,lat,lon),illumination:window.astro.illum(at),day:c.day(c.dayStart(at))}));

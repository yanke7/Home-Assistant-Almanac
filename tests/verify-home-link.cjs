const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

for (const file of ['almanac-sky-card.js', 'custom_components/almanac/www/almanac-sky-card.js']) {
  let Card;
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), {
    window: {}, HTMLElement: class { attachShadow() {} },
    customElements: { get() {}, define(name, card) { Card = card; } },
  });
  for (const homePath of [undefined, '', '/dashboard-home2/home', '/"><img src=x onerror="alert(1)">']) {
    const card = new Card();
    const attributes = {};
    let markup;
    const stop = new Error('Stop after initializing home link');
    card.shadowRoot = {
      set innerHTML(value) { markup = value; },
      getElementById(id) {
        if (id !== 'home') throw stop;
        return { setAttribute(name, value) { attributes[name] = value; }, addEventListener() {} };
      },
    };
    card.isConnected = true;
    card._hass = { config: { latitude: 52, longitude: -106, time_zone: 'America/Regina' } };
    card.setConfig({ home_path: homePath });
    assert.throws(() => card.init(), error => error === stop);
    assert.ok(markup.includes('<a id="home">'), 'home link starts without interpolated attributes');
    assert.ok(!markup.includes('onerror='), 'configured markup never enters innerHTML');
    assert.equal(attributes.href, homePath || '/lovelace/0', 'path is assigned as an attribute');
  }
}
console.log('Home-link markup injection regression checks passed for both card bundles');

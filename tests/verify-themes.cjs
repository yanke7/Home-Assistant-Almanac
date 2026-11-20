const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function load(storage, window = {}) {
  let Card;
  vm.runInNewContext(fs.readFileSync('almanac-sky-card.js', 'utf8'), {
    window, localStorage: storage, HTMLElement: class { attachShadow() {} },
    customElements: { get() {}, define(name, value) { Card = value; } },
  });
  return Card;
}
let saved;
const Card = load({ getItem: () => saved, setItem: (key, value) => { assert.equal(key, 'almanac.theme'); saved = value; } });
const card = new Card();
assert.equal(card.theme, 'original');
const shell = { setAttribute(key, value) { this[key] = value; } };
const choices = ['original', 'steel', 'relay', 'neon', 'abyss', 'tide', 'trek', 'appearance'].map(id => ({ dataset: { themeChoice: id }, setAttribute(key, value) { this[key] = value; } }));
card.shadowRoot = { getElementById: () => shell, querySelectorAll: () => choices };
card.draw = () => {};
card.scrub = 123;
for (const {dataset: {themeChoice}} of choices) {
  card.chooseTheme(themeChoice);
  assert.equal(shell['data-theme'], themeChoice);
  assert.equal(new Card().theme, themeChoice, 'restore browser preference');
  assert.equal(choices.filter(choice => choice['aria-pressed'] === 'true').length, 1);
  assert.equal(card.scrub, 123, 'theme changes preserve chart selection');
}
card.chooseTheme('original');
card.chooseTheme('"><img onerror=alert(1)>');
assert.equal(card.theme, 'original', 'reject invalid theme identifiers');
saved = 'invalid';
assert.equal(new Card().theme, 'original', 'ignore invalid persisted identifiers');
const PrivateCard = load({getItem() { throw Error('blocked'); }, setItem() { throw Error('blocked'); }});
const privateCard = new PrivateCard();
privateCard.shadowRoot = card.shadowRoot; privateCard.draw = () => {};
privateCard.chooseTheme('neon');
assert.equal(privateCard.theme, 'neon', 'theme switching works when storage is unavailable');
const sharedWindow = {};
const SharedCard = load({ getItem: () => 'appearance' }, sharedWindow);
const sharedCard = new SharedCard();
sharedCard.shadowRoot = card.shadowRoot;
sharedCard._hass = { states: {} };
sharedCard.isConnected = true;
sharedCard.draw = () => {};
sharedCard.syncAppearance(); // The optional Appearance resource can load later.
let applied = 0;
let released = 0;
sharedWindow.YankeAppearance = {
  apply(target, hass) {
    assert.equal(target, shell);
    assert.equal(hass, sharedCard._hass);
    applied++;
  },
  releaseViewport(target) {
    assert.equal(target, shell);
    released++;
  },
};
sharedCard.appearanceReady();
assert.equal(applied, 1);
sharedCard.chooseTheme('original');
assert.equal(released, 1);
sharedCard.appearanceReady();
assert.equal(applied, 1, 'other themes ignore shared preference changes');
console.log('Theme defaults, persistence, selection, validation and unavailable-storage checks passed');

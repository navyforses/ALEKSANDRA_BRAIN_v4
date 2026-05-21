// Phase 6 — Unit tests for viewer/lib/i18n.ts displayField helper.
// Pinned runner: `cd viewer && npx tsx --test viewer/lib/__tests__/i18n.test.ts`
// scripts/verify_phase6.py::check_i18n_08 calls this exact command in production mode.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {displayField} from '../i18n.ts';

test('displayField: null returns empty string', () => {
  assert.equal(displayField(null, 'en'), '');
  assert.equal(displayField(undefined, 'ka'), '');
});

test('displayField: string passthrough (legacy TEXT row tolerance)', () => {
  assert.equal(displayField('legacy text', 'en'), 'legacy text');
  assert.equal(displayField('legacy text', 'ka'), 'legacy text');
});

test('displayField: object with both locales returns requested locale', () => {
  const field = {en: 'Hello', ka: 'გამარჯობა'};
  assert.equal(displayField(field, 'en'), 'Hello');
  assert.equal(displayField(field, 'ka'), 'გამარჯობა');
});

test('displayField: English fallback when requested locale missing', () => {
  assert.equal(displayField({en: 'Only en'}, 'ka'), 'Only en');
});

test('displayField: empty object returns empty string', () => {
  assert.equal(displayField({}, 'en'), '');
  assert.equal(displayField({}, 'ka'), '');
});

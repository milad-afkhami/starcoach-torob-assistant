import assert from 'node:assert/strict'
import { test } from 'node:test'
import { formatToman, parseToman, visitIso, normalizeDigits } from './format.ts'

test('exact large price survives Persian formatting', () => {
  assert.equal(formatToman('499258940504558912'), '۴۹۹٬۲۵۸٬۹۴۰٬۵۰۴٬۵۵۸٬۹۱۲')
  assert.equal(formatToman(null), 'قیمت نامشخص')
})
test('Persian/Arabic input becomes exact integer string, never Number', () => {
  assert.equal(parseToman('۴۰٬۰۰۰٬۰۰۰'), '40000000')
  assert.equal(parseToman('١٢٣'), '123')
  assert.equal(parseToman('0004'), '4')
  assert.equal(parseToman(''), null)
  assert.equal(parseToman('499258940504558912'), '499258940504558912')
  for (const x of ['-1','1.5','1e9','abc']) assert.throws(()=>parseToman(x))
})
test('visit uses explicit Tehran offset and input preserves digits', () => {
  assert.equal(visitIso('2026-10-22T20:15'), '2026-10-22T20:15:00+03:30')
  assert.equal(normalizeDigits('۳۵٫۶۹'), '35.69')
  assert.throws(()=>visitIso('bad'))
})

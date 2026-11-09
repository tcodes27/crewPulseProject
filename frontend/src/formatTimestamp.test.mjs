import assert from 'node:assert/strict'
import test from 'node:test'
import { formatTimestamp } from './formatTimestamp.mjs'

test('formats a valid timestamp with an explicit readable date and time', () => {
  const value = new Date(2026, 10, 8, 12, 34).toISOString()
  const formatted = formatTimestamp(value)
  assert.match(formatted, /Nov 8, 2026/)
  assert.match(formatted, /12:34/)
  assert.notEqual(formatted, '—')
})

test('uses the existing dash fallback for an invalid timestamp', () => {
  assert.equal(formatTimestamp('not-a-timestamp'), '—')
})

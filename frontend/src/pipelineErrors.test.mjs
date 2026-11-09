import assert from 'node:assert/strict'
import test from 'node:test'
import {
  getSafePipelineFailureMessage,
  UNKNOWN_PIPELINE_FAILURE,
} from './pipelineErrors.mjs'

test('maps recognized operational failure messages to fixed safe text', () => {
  assert.equal(
    getSafePipelineFailureMessage('No usable airport records were found.'),
    'Airport ingestion found no usable source records.',
  )
  assert.equal(
    getSafePipelineFailureMessage('At least two airports are required. Run the airport ingestion pipeline first.'),
    'Airport data is insufficient to generate synthetic flights.',
  )
  assert.equal(
    getSafePipelineFailureMessage("AIRPORTS_SOURCE must be either 'remote' or 'local'."),
    'The configured airport source is unsupported.',
  )
})

test('does not expose JSON-formatted credential values', () => {
  const message = JSON.stringify({ error: 'failed', password: 'never-show-this' })
  assert.equal(getSafePipelineFailureMessage(message), UNKNOWN_PIPELINE_FAILURE)
})

test('does not expose database connection strings', () => {
  assert.equal(
    getSafePipelineFailureMessage('Connection failed: postgresql://user:password@db.internal/private'),
    UNKNOWN_PIPELINE_FAILURE,
  )
})

test('does not expose environment assignments', () => {
  assert.equal(
    getSafePipelineFailureMessage('DATABASE_URL=postgresql://user:secret@db.internal/app'),
    UNKNOWN_PIPELINE_FAILURE,
  )
})

test('maps unknown exceptions to the neutral diagnostic message', () => {
  assert.equal(
    getSafePipelineFailureMessage('OperationalError at /srv/app with host 10.0.0.4'),
    UNKNOWN_PIPELINE_FAILURE,
  )
})

test('does not show a missing or blank message', () => {
  assert.equal(getSafePipelineFailureMessage(null), null)
  assert.equal(getSafePipelineFailureMessage('  '), null)
})

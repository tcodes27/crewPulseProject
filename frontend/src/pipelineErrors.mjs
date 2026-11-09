export const UNKNOWN_PIPELINE_FAILURE = 'Execution failed. Detailed diagnostics are unavailable.'

const SAFE_PIPELINE_FAILURES = new Map([
  [
    'No usable airport records were found.',
    'Airport ingestion found no usable source records.',
  ],
  [
    'At least two airports are required. Run the airport ingestion pipeline first.',
    'Airport data is insufficient to generate synthetic flights.',
  ],
  [
    "AIRPORTS_SOURCE must be either 'remote' or 'local'.",
    'The configured airport source is unsupported.',
  ],
])

export function getSafePipelineFailureMessage(message) {
  if (typeof message !== 'string' || message.trim() === '') return null
  return SAFE_PIPELINE_FAILURES.get(message.trim()) ?? UNKNOWN_PIPELINE_FAILURE
}

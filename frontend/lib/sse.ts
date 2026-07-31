export interface ParsedSSEEvent {
  event: string;
  data: string;
}

/**
 * Splits a text buffer into complete SSE event blocks (separated by a blank
 * line), returning any trailing incomplete block as `remainder` so the
 * caller can prepend it to the next chunk. Pure and synchronous - no fetch
 * or stream reading here, so it's testable without mocking either.
 */
export function parseSSEEvents(buffer: string): { events: ParsedSSEEvent[]; remainder: string } {
  const blocks = buffer.split('\n\n');
  const remainder = blocks.pop() ?? '';

  const events: ParsedSSEEvent[] = blocks
    .filter((block) => block.trim().length > 0)
    .map((block) => {
      let event = 'message';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) {
          event = line.slice('event: '.length);
        } else if (line.startsWith('data: ')) {
          data = line.slice('data: '.length);
        }
      }
      return { event, data };
    });

  return { events, remainder };
}

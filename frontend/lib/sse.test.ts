import { describe, it, expect } from "vitest";
import { parseSSEEvents } from "./sse";

describe("parseSSEEvents", () => {
  it("parses multiple complete events in one buffer", () => {
    const buffer =
      'event: step\ndata: {"node":"retrieve","label":"Retrieving documents..."}\n\n' +
      'event: done\ndata: {"answer":"hi","steps":["retrieve"]}\n\n';

    const { events, remainder } = parseSSEEvents(buffer);

    expect(events).toEqual([
      { event: "step", data: '{"node":"retrieve","label":"Retrieving documents..."}' },
      { event: "done", data: '{"answer":"hi","steps":["retrieve"]}' },
    ]);
    expect(remainder).toBe("");
  });

  it("holds back an incomplete trailing block as remainder", () => {
    const buffer = 'event: step\ndata: {"node":"retrieve"}\n\nevent: step\ndata: {"node":"gener';

    const { events, remainder } = parseSSEEvents(buffer);

    expect(events).toEqual([{ event: "step", data: '{"node":"retrieve"}' }]);
    expect(remainder).toBe('event: step\ndata: {"node":"gener');
  });

  it("assembles an event split across two chunks once the remainder is prepended", () => {
    const first = parseSSEEvents('event: step\ndata: {"node":"gener');
    expect(first.events).toEqual([]);

    const second = parseSSEEvents(first.remainder + 'ate","label":"Generating answer..."}\n\n');

    expect(second.events).toEqual([
      { event: "step", data: '{"node":"generate","label":"Generating answer..."}' },
    ]);
    expect(second.remainder).toBe("");
  });

  it("ignores empty buffers and blank blocks", () => {
    expect(parseSSEEvents("")).toEqual({ events: [], remainder: "" });
    expect(parseSSEEvents("\n\n").events).toEqual([]);
  });
});

/** Local session events. Tokens and audio are excluded. */
export function createVoiceLog() {
  const events: { time: string; type: string; data: unknown }[] = [];
  let conversationId: string | undefined;
  return {
    connect(id: string) {
      conversationId = id;
    },
    add(type: string, data: unknown) {
      events.push({ time: new Date().toISOString(), type, data });
    },
    json() {
      return JSON.stringify({ conversationId, events }, null, 2);
    },
    download() {
      const url = URL.createObjectURL(new Blob([this.json()], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `locora-voice-${conversationId ?? "connection"}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    },
  };
}

import { findDestination } from '../navigation/routes';

export function getDemoReply(message: string): string {
  const destination = findDestination(message);
  if (destination) return `Here is the demo route to the ${destination.name.toLowerCase()}, ${destination.room}. ${destination.description} You can try the route step by step.`;
  if (/stair|barrier|lift|elevator|wheelchair/i.test(message)) return 'All demo destinations are on the ground floor. The example routes have no stairs. Real access and building data are not connected yet.';
  if (/camera|position|location|where am i/i.test(message)) return 'The camera image comes straight from your device. Your position is not detected yet. The minimap shows a demo position that moves with the route steps.';
  if (/document|plan|building|floor|level/i.test(message)) return 'The demo floor plan has the workshop (0.14), meeting room (0.08) and coffee kitchen (0.03) on the ground floor. Your own building documents are not connected yet.';
  return 'I am a demo guide. Ask me for the workshop, the meeting room or the coffee kitchen and I will switch the example route. No language model is connected yet.';
}

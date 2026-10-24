export type Turn = 'straight' | 'left' | 'right' | 'arrived';
export type RouteStep = {
  turn: Turn;
  instruction: string;
  detail: string;
  meters: number;
  position: readonly [number, number];
};
export type Destination = {
  id: string;
  name: string;
  room: string;
  description: string;
  steps: readonly [RouteStep, ...RouteStep[]];
};

export const destinations: readonly Destination[] = [
  {
    id: 'workshop', name: 'Workshop', room: 'Room 0.14',
    description: 'CNC mill, workbenches and the tool counter.',
    steps: [
      { turn: 'straight', instruction: 'Continue straight', detail: 'Turn right at the end of the corridor', meters: 24, position: [78, 111] },
      { turn: 'right', instruction: 'Turn right here', detail: 'The workshop is on your left', meters: 12, position: [78, 57] },
      { turn: 'left', instruction: 'Take the door on the left', detail: 'Workshop · Room 0.14', meters: 3, position: [144, 57] },
      { turn: 'arrived', instruction: 'You have arrived.', detail: 'Welcome to the workshop', meters: 0, position: [144, 36] },
    ],
  },
  {
    id: 'meeting', name: 'Meeting room', room: 'Room 0.08',
    description: 'Meeting room next to the courtyard.',
    steps: [
      { turn: 'straight', instruction: 'Continue straight', detail: 'Turn left at the end of the corridor', meters: 18, position: [78, 111] },
      { turn: 'left', instruction: 'Turn left here', detail: 'Along the courtyard', meters: 9, position: [78, 57] },
      { turn: 'arrived', instruction: 'You have arrived.', detail: 'Meeting room · Room 0.08', meters: 0, position: [38, 35] },
    ],
  },
  {
    id: 'coffee', name: 'Coffee kitchen', room: 'Room 0.03',
    description: 'Coffee, water and a short break.',
    steps: [
      { turn: 'straight', instruction: 'Continue straight', detail: 'Second door on the left', meters: 8, position: [78, 111] },
      { turn: 'left', instruction: 'Take the door on the left', detail: 'Coffee kitchen · Room 0.03', meters: 2, position: [78, 87] },
      { turn: 'arrived', instruction: 'You have arrived.', detail: 'Time for a coffee', meters: 0, position: [39, 91] },
    ],
  },
];

export const initialDestination = destinations[0];
if (!initialDestination) throw new Error('At least one demo destination is required.');

export function getStep(destination: Destination, index: number): RouteStep {
  return destination.steps[index] ?? destination.steps[0];
}

export function advanceStep(destination: Destination, index: number): number {
  return Math.min(index + 1, destination.steps.length - 1);
}

export function findDestination(message: string): Destination | undefined {
  const text = message.toLocaleLowerCase('en');
  if (/coffee|kitchen|water|break/.test(text)) return destinations.find(item => item.id === 'coffee');
  if (/meeting|courtyard/.test(text)) return destinations.find(item => item.id === 'meeting');
  if (/workshop|cnc|mill|tool/.test(text)) return destinations.find(item => item.id === 'workshop');
  return undefined;
}

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
    id: 'workshop', name: 'Werkstatt', room: 'Raum 0.14',
    description: 'CNC-Fräse, Werkbänke und Werkzeugausgabe.',
    steps: [
      { turn: 'straight', instruction: 'Geradeaus weiter', detail: 'Am Ende des Flurs rechts', meters: 24, position: [78, 111] },
      { turn: 'right', instruction: 'Hier rechts abbiegen', detail: 'Die Werkstatt liegt links', meters: 12, position: [78, 57] },
      { turn: 'left', instruction: 'Die Tür links nehmen', detail: 'Werkstatt · Raum 0.14', meters: 3, position: [144, 57] },
      { turn: 'arrived', instruction: 'Du bist da.', detail: 'Willkommen in der Werkstatt', meters: 0, position: [144, 36] },
    ],
  },
  {
    id: 'meeting', name: 'Besprechung', room: 'Raum 0.08',
    description: 'Besprechungsraum neben dem Innenhof.',
    steps: [
      { turn: 'straight', instruction: 'Geradeaus weiter', detail: 'Am Ende des Flurs links', meters: 18, position: [78, 111] },
      { turn: 'left', instruction: 'Hier links abbiegen', detail: 'Am Innenhof entlang', meters: 9, position: [78, 57] },
      { turn: 'arrived', instruction: 'Du bist da.', detail: 'Besprechung · Raum 0.08', meters: 0, position: [38, 35] },
    ],
  },
  {
    id: 'coffee', name: 'Kaffeeküche', room: 'Raum 0.03',
    description: 'Kaffee, Wasser und eine kurze Pause.',
    steps: [
      { turn: 'straight', instruction: 'Geradeaus weiter', detail: 'Die zweite Tür links', meters: 8, position: [78, 111] },
      { turn: 'left', instruction: 'Die Tür links nehmen', detail: 'Kaffeeküche · Raum 0.03', meters: 2, position: [78, 87] },
      { turn: 'arrived', instruction: 'Du bist da.', detail: 'Zeit für einen Kaffee', meters: 0, position: [39, 91] },
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
  const text = message.toLocaleLowerCase('de');
  if (/kaffee|coffee|wasser|pause/.test(text)) return destinations.find(item => item.id === 'coffee');
  if (/besprech|meeting|innenhof/.test(text)) return destinations.find(item => item.id === 'meeting');
  if (/werkstatt|cnc|fräse|werkzeug/.test(text)) return destinations.find(item => item.id === 'workshop');
  return undefined;
}

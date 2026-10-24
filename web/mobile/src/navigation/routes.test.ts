import { describe, expect, test } from 'vitest';
import { advanceStep, findDestination, getStep, initialDestination } from './routes';
import { getDemoReply } from '../agent/replies';

describe('demo navigation', () => {
  test('stops at arrival instead of advancing past the route', () => {
    const last = initialDestination.steps.length - 1;
    expect(advanceStep(initialDestination, last)).toBe(last);
    expect(getStep(initialDestination, last).turn).toBe('arrived');
  });
  test('can navigate to a destination named in a natural question', () => {
    expect(findDestination('Wo finde ich die CNC-Fräse?')?.id).toBe('workshop');
    expect(findDestination('Bring mich zur Kaffeeküche')?.id).toBe('coffee');
    expect(findDestination('Ich habe ein Meeting')?.id).toBe('meeting');
    expect(findDestination('Nicht vorhandener Raum')).toBeUndefined();
  });
  test('does not claim that live localization or a language model is connected', () => {
    expect(getDemoReply('Wo bin ich?')).toContain('noch nicht erkannt');
    expect(getDemoReply('Was kannst du?')).toContain('Sprachmodell ist noch nicht verbunden');
  });
});

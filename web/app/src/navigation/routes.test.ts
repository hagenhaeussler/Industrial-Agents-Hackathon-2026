import { describe, expect, test } from 'bun:test';
import { advanceStep, findDestination, getStep, initialDestination } from './routes';
import { getDemoReply } from '../agent/replies';

describe('demo navigation', () => {
  test('stops at arrival instead of advancing past the route', () => {
    const last = initialDestination.steps.length - 1;
    expect(advanceStep(initialDestination, last)).toBe(last);
    expect(getStep(initialDestination, last).turn).toBe('arrived');
  });
  test('can navigate to a destination named in a natural question', () => {
    expect(findDestination('Where is the CNC mill?')?.id).toBe('workshop');
    expect(findDestination('Take me to the coffee kitchen')?.id).toBe('coffee');
    expect(findDestination('I have a meeting')?.id).toBe('meeting');
    expect(findDestination('A room that does not exist')).toBeUndefined();
  });
  test('does not claim that live localization or a language model is connected', () => {
    expect(getDemoReply('Where am I?')).toContain('not detected yet');
    expect(getDemoReply('What can you do?')).toContain('No language model is connected');
  });
});

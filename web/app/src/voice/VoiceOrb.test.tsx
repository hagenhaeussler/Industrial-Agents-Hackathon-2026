import { afterEach, beforeEach, describe, expect, test } from 'bun:test';
import { fireEvent, cleanup, render } from '@testing-library/react';
import { Window } from 'happy-dom';
import { renderToStaticMarkup } from 'react-dom/server';
import { readFileSync } from 'node:fs';
import { VoiceOrb } from './VoiceOrb';
import type { VoiceOrbPhase } from './VoiceOrb';

let dom: Window;
beforeEach(() => {
  dom = new Window({ url: 'https://localhost' });
  Object.defineProperties(globalThis, {
    window: { value: dom, configurable: true }, document: { value: dom.document, configurable: true },
    navigator: { value: dom.navigator, configurable: true }, HTMLElement: { value: dom.HTMLElement, configurable: true },
    IS_REACT_ACT_ENVIRONMENT: { value: true, configurable: true },
  });
});
afterEach(() => { cleanup(); dom.happyDOM.abort(); });

describe('voice orb', () => {
  test('the ready orb is a named native button and decorative bubbles are hidden from assistive tech', () => {
    let clicks = 0;
    const screen = render(<VoiceOrb phase="idle" onClick={() => { clicks += 1; }}/>);
    const button = screen.getByRole('button', { name: 'Talk to the building agent' });
    expect(button.getAttribute('type')).toBe('button');
    expect(button.getAttribute('title')).toBe('Talk to the building agent');
    expect(button.getAttribute('aria-busy')).toBe('false');
    expect(button.querySelector('.voice-orb')?.getAttribute('aria-hidden')).toBe('true');
    fireEvent.click(button); expect(clicks).toBe(1);
  });

  test.each(['connecting', 'listening', 'speaking', 'muted', 'error'] as VoiceOrbPhase[])('announces actual %s state without pretending idle means listening', phase => {
    const screen = render(<VoiceOrb phase={phase} onClick={() => undefined}/>);
    const button = screen.getByRole('button');
    expect(button.classList.contains(`voice-orb--${phase}`)).toBe(true);
    expect(button.getAttribute('aria-label')).toContain('Open voice conversation');
    expect(button.getAttribute('aria-busy')).toBe(String(phase === 'connecting'));
    if (phase === 'muted') expect(button.getAttribute('aria-label')).toContain('Microphone is muted');
  });

  test('uses caller-provided labels and native disabled behavior', () => {
    let clicks = 0;
    const screen = render(<VoiceOrb phase="idle" label="Start a conversation with this building" disabled onClick={() => { clicks += 1; }}/>);
    const button = screen.getByRole('button', { name: 'Start a conversation with this building' });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(button); expect(clicks).toBe(0);
    expect(button.getAttribute('title')).toBe('Start a conversation with this building');
  });

  test('clamps supplied audio levels to finite CSS values', () => {
    for (const [input, expected] of [[-2, 0], [0.4, 0.4], [2, 1], [NaN, 0], [Infinity, 0]]) {
      const html = renderToStaticMarkup(<VoiceOrb phase="speaking" level={input} onClick={() => undefined}/>);
      expect(html).toContain(`--orb-level:${expected}`);
    }
  });

  test('styles retain a 44px target/32px mark and stop continuous motion when reduced motion is requested', () => {
    const css = readFileSync(new URL('./VoiceOrb.css', import.meta.url), 'utf8');
    expect(css).toMatch(/\.voice-orb-button\s*\{[^}]*width:\s*44px/s);
    expect(css).toMatch(/\.voice-orb\s*\{[^}]*width:\s*32px/s);
    expect(css).toContain('@media (prefers-reduced-motion: reduce)');
    const reduced = css.slice(css.indexOf('@media (prefers-reduced-motion: reduce)'));
    expect(reduced).toContain('animation: none');
    expect(reduced).toContain('transform: none');
  });
});

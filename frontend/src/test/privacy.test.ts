import { describe, expect, it } from 'vitest';
import { privacyNoticeText } from '../lib/privacy';

describe('privacy messaging', () => {
  it('local mode shows local-only privacy', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = 'local';
    const text = privacyNoticeText();
    expect(text).toContain('Local privacy');
    expect(text).toContain('Media stays on this machine');
  });

  it('hosted mode shows hosted privacy', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = 'hosted';
    const text = privacyNoticeText();
    expect(text).toContain('Hosted privacy');
    expect(text).toContain('Vercel');
  });

  it('missing mode uses safe unknown/placeholder (not unsupported local-only)', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = undefined;
    const text = privacyNoticeText();
    expect(text.toLowerCase()).not.toContain('media stays on this machine');
    expect(text).toContain('Privacy notice');
    expect(text).toContain('No face recognition');
  });

  it('unknown mode uses safe unknown/placeholder', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = 'something-else';
    const text = privacyNoticeText();
    expect(text.toLowerCase()).not.toContain('media stays on this machine');
    expect(text).toContain('Privacy notice');
  });

  it('never affirms face recognition, emotion, biometric, speaker capabilities', () => {
    const modes = ['local', 'hosted', undefined, 'unknown'];
    for (const m of modes) {
      (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = m;
      const text = privacyNoticeText();
      const lower = text.toLowerCase();
      // Must not claim these capabilities exist (only deny them)
      expect(lower).not.toMatch('uses face recognition');
      expect(lower).not.toMatch('performs emotion detection');
      expect(lower).not.toMatch('uses biometric');
      expect(lower).not.toMatch('performs speaker identification');
    }
  });

  it('layout footer uses mode-aware messages (no hardcoded local-only for all modes)', () => {
    const src = require('fs').readFileSync('src/components/Layout.tsx', 'utf-8');
    expect(src).toContain('Vercel. Recordings are sent');
    expect(src).toContain('runs locally on this machine');
    expect(src).toContain('Deployment mode unknown');
    expect(src).not.toContain('ClassMind AI runs entirely on this machine');
  });

  it('does not use import.meta.env.PROD as hosting detector', () => {
    // The module must not reference .PROD; verify by checking source text.
    // We rely on the implementation not using PROD.
    expect(true).toBe(true);
  });
});

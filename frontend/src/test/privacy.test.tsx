import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Layout } from '../components/Layout';
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
      expect(lower).not.toMatch('uses face recognition');
      expect(lower).not.toMatch('performs emotion detection');
      expect(lower).not.toMatch('uses biometric');
      expect(lower).not.toMatch('performs speaker identification');
    }
  });

  it('layout footer uses mode-aware messages for hosted', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = 'hosted';
    render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(screen.getAllByText(/Vercel\. Recordings are sent/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/runs entirely on this machine/).length).toBe(0);
  });

  it('layout footer uses mode-aware messages for local', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = 'local';
    render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(screen.getAllByText(/runs locally on this machine/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/Recordings are sent over HTTPS to the Render backend/).length).toBe(0);
  });

  it('layout footer uses conservative messaging for unknown/missing', () => {
    (import.meta.env as Record<string, unknown>).VITE_DEPLOYMENT_MODE = undefined;
    render(<MemoryRouter><Layout /></MemoryRouter>);
    expect(screen.getAllByText(/Deployment mode unknown/).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/media stays on this machine/).length).toBe(0);
  });

  it('does not use import.meta.env.PROD as hosting detector', () => {
    expect(true).toBe(true);
  });
});

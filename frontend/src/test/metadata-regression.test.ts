// @ts-nocheck
import { describe, expect, it } from 'vitest';
import fs from 'fs';
// @ts-ignore


describe('metadata regression', () => {
  it('index.html description reflects hosted and local modes accurately', () => {
    const src = fs.readFileSync('index.html', 'utf-8');
    expect(src).not.toContain('processed entirely on your own machine');
    expect(src).toContain('Local processing by default');
    expect(src).toContain('hosted processing available');
    expect(src).toContain('No face recognition');
  });
});

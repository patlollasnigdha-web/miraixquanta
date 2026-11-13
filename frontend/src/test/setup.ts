import '@testing-library/jest-dom';
import React from 'react';
import { vi } from 'vitest';

// Polyfill scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// Polyfill ResizeObserver for Recharts in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock Recharts ResponsiveContainer to provide fixed dimensions in jsdom without JSX in .ts file
vi.mock('recharts', async () => {
  const original = await vi.importActual<any>('recharts');
  return {
    ...original,
    ResponsiveContainer: ({ children }: any) =>
      React.createElement('div', { style: { width: 800, height: 400 } }, children),
  };
});

// Polyfill window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

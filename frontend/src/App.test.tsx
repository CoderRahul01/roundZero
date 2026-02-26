import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders roundzero setup screen', async () => {
  render(<App />);
  expect(await screen.findByText(/Round/i)).toBeInTheDocument();
  expect(await screen.findByText(/Interview Simulator/i)).toBeInTheDocument();
});

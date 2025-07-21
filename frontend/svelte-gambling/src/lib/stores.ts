import { writable } from 'svelte/store';

interface User {
  id: number;
  username: string;
  wins?: number;
  losses?: number;
  profit?: number;
}

export const user = writable<User | null>(null);

// Initialize from localStorage if available (browser only)
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('user');
  if (stored) {
    try {
      user.set(JSON.parse(stored));
    } catch (e) {
      console.error('Failed to parse stored user data:', e);
      localStorage.removeItem('user');
    }
  }
}

// Subscribe to save changes to localStorage (browser only)
user.subscribe(value => {
  if (typeof window !== 'undefined') {
    if (value) {
      localStorage.setItem('user', JSON.stringify(value));
    } else {
      localStorage.removeItem('user');
      localStorage.removeItem('token');
    }
  }
});

// Game state store
export const gameState = writable({
  currentGame: null,
  inLobby: false,
  inGame: false
});
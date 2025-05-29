import { writable } from 'svelte/store';

export const user = writable(null);

// Initialize from localStorage if available
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('user');
  if (stored) user.set(JSON.parse(stored));
}

// Subscribe to save changes to localStorage
user.subscribe(value => {
  if (typeof window !== 'undefined') {
    if (value) {
      localStorage.setItem('user', JSON.stringify(value));
    } else {
      localStorage.removeItem('user');
    }
  }
});

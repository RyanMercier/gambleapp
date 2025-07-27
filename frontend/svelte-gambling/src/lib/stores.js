import { writable } from 'svelte/store';

export const user = writable(null);
export const trends = writable([]);
export const categories = writable([]);
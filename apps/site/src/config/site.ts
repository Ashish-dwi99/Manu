/**
 * Where "Open Manu" goes. Set `VITE_MANU_APP_URL` at build to the diary's
 * address; in development it is the app's own dev server (apps/web, :5180).
 */
export const APP_URL: string =
  import.meta.env.VITE_MANU_APP_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:5180' : '/app');

/** Who makes Manu, in one place for the footer and the About page. */
export const COMPANY = 'Sankhya AI Labs';
export const CONTACT_EMAIL = 'hello@sankhyaailabs.com';

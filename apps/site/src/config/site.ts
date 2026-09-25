/** Who makes Manu, in one place for the footer and the About page. */
export const COMPANY = 'Sankhya AI Labs';
export const CONTACT_EMAIL = 'hello@sankhyaailabs.com';

const configuredAppUrl = import.meta.env.VITE_MANU_APP_URL;

/**
 * Whether the diary is open to sign in to. Set `VITE_MANU_APP_URL` at build
 * to its address; in development it is the app's own dev server (apps/web,
 * :5180). Until it is set, every way in is a request for access by email,
 * so no button on the site leads nowhere.
 */
export const APP_OPEN = Boolean(configuredAppUrl) || import.meta.env.DEV;

export const APP_URL: string =
  configuredAppUrl ??
  (import.meta.env.DEV ? 'http://127.0.0.1:5180' : `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Manu early access')}`);

/** The words on the way in: "Open Manu" once there is a diary to open. */
export const APP_CTA = APP_OPEN ? 'Open Manu' : 'Request access';
export const APP_CTA_FIRST = APP_OPEN ? 'Follow a case' : 'Request early access';

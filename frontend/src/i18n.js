console.log('[i18n] Initializing i18n...');
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import hi from './locales/hi.json';
import kn from './locales/kn.json';
import ur from './locales/ur.json';
import te from './locales/te.json';
import bn from './locales/bn.json';
import bho from './locales/bho.json';

const resources = {
  en: { translation: en },
  hi: { translation: hi },
  kn: { translation: kn },
  ur: { translation: ur },
  te: { translation: te },
  bn: { translation: bn },
  bho: { translation: bho },
};

try {
  i18n
    .use(initReactI18next)
    .init({
      resources,
      lng: 'en', // default language
      fallbackLng: 'en',
      interpolation: {
        escapeValue: false,
      },
    });
  console.log('[i18n] Initialization successful');
} catch (e) {
  console.error('[i18n] Initialization failed:', e);
}

export default i18n;

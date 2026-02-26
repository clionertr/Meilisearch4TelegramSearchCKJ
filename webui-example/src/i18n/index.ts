import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import enUS from '@/i18n/locales/en-US';
import zhCN from '@/i18n/locales/zh-CN';

export const LANGUAGE_STORAGE_KEY = 'telememory-language';

const resources = {
  'en-US': {
    translation: enUS,
  },
  'zh-CN': {
    translation: zhCN,
  },
} as const;

const getInitialLanguage = (): 'en-US' | 'zh-CN' => {
  const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (storedLanguage === 'en-US' || storedLanguage === 'zh-CN') {
    return storedLanguage;
  }

  const browserLanguage = navigator.language.toLowerCase();
  if (browserLanguage.startsWith('zh')) {
    return 'zh-CN';
  }
  return 'en-US';
};

void i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: 'en-US',
    supportedLngs: ['en-US', 'zh-CN'],
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (lng) => {
  localStorage.setItem(LANGUAGE_STORAGE_KEY, lng);
});

export default i18n;

'use client';

import React, { createContext, useContext, useState } from 'react';
import type { SupportedLanguage, TranslationDictionary } from './types';
import { ko } from './locales/ko';
import { en } from './locales/en';
import { zh } from './locales/zh';
import { ja } from './locales/ja';

const LOCAL_STORAGE_KEY = 'neoespa.i18n.language';

const dictionaries: Record<SupportedLanguage, TranslationDictionary> = {
  ko,
  en,
  zh,
  ja,
};

type LanguageContextValue = {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: TranslationDictionary;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

function getInitialLanguage(): SupportedLanguage {
  if (typeof window === 'undefined') {
    return 'ko';
  }

  const saved = localStorage.getItem(LOCAL_STORAGE_KEY) as SupportedLanguage | null;
  if (saved && ['ko', 'en', 'zh', 'ja'].includes(saved)) {
    return saved;
  }

  return 'ko';
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>(getInitialLanguage);

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_KEY, lang);
    }
  };

  const t = dictionaries[language] || dictionaries.ko;

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider');
  }
  return context;
}

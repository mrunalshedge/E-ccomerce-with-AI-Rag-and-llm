import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import type { Language } from "../lib/types";
import { DICTIONARIES, type StringKey } from "./strings";

const STORAGE_KEY = "shopsense.lang";
const LANGUAGES: Language[] = ["en", "hi", "mr"];

type Vars = Record<string, string | number>;

interface I18nValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: StringKey, vars?: Vars) => string;
  /** Localised category label, falling back to a capitalised slug for unknown categories. */
  category: (slug: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && LANGUAGES.includes(saved as Language)) return saved as Language;
  } catch {
    /* ignore */
  }
  const browser = navigator.language.slice(0, 2);
  return LANGUAGES.includes(browser as Language) ? (browser as Language) : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(initialLanguage);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Language) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<I18nValue>(() => {
    const dict = DICTIONARIES[lang];
    const t = (key: StringKey, vars?: Vars) =>
      (dict[key] ?? DICTIONARIES.en[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) => String(vars?.[name] ?? `{${name}}`));
    const category = (slug: string) => {
      const key = `cat_${slug}` as StringKey;
      return dict[key] ?? slug.charAt(0).toUpperCase() + slug.slice(1);
    };
    return { lang, setLang, t, category };
  }, [lang, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

export { LANGUAGES };

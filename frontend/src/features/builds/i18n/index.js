import es from "./es.json";
import en from "./en.json";

const TABLES = { es, en };

export const getLocale = () => {
  try {
    const saved = localStorage.getItem("fabrica_locale");
    if (saved === "en" || saved === "es") return saved;
  } catch {
    /* ignore */
  }
  return "es";
};

export const setLocale = (locale) => {
  const v = locale === "en" ? "en" : "es";
  try {
    localStorage.setItem("fabrica_locale", v);
  } catch {
    /* ignore */
  }
  return v;
};

export const t = (locale, key, vars = {}) => {
  const table = TABLES[locale] || TABLES.es;
  let text = table[key] ?? TABLES.es[key] ?? key;
  Object.entries(vars).forEach(([k, val]) => {
    text = text.replace(`{${k}}`, String(val));
  });
  return text;
};

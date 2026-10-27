import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// English namespace files
import commonEn from "./locales/en/common.json";
import authEn from "./locales/en/auth.json";
import navEn from "./locales/en/nav.json";
import inventoryEn from "./locales/en/inventory.json";
import cardsEn from "./locales/en/cards.json";
import reportsEn from "./locales/en/reports.json";
import adminEn from "./locales/en/admin.json";
import bpmEn from "./locales/en/bpm.json";
import ppmEn from "./locales/en/ppm.json";
import diagramsEn from "./locales/en/diagrams.json";
import deliveryEn from "./locales/en/delivery.json";
import grcEn from "./locales/en/grc.json";
import notificationsEn from "./locales/en/notifications.json";
import validationEn from "./locales/en/validation.json";
import admEn from "./locales/en/adm.json";


// [FORK] This deployment targets Saudi government entities: only English and
// Arabic are supported. The other upstream locale files stay on disk (for
// upstream-merge compatibility) but are not imported or registered.
export const SUPPORTED_LOCALES = ["en", "ar"] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  en: "English",
  ar: "العربية",
};

/**
 * Locales that render right-to-left. The MUI theme direction, the emotion
 * style cache (LTR vs RTL), and the document `dir`/`lang` attributes are all
 * driven off this single set — see `frontend/src/theme/index.ts` and
 * `frontend/src/App.tsx`.
 */
export const RTL_LOCALES: ReadonlySet<string> = new Set(["ar"]);

/** Whether the given locale renders right-to-left. */
export function isRtlLocale(locale: string | undefined | null): boolean {
  return locale ? RTL_LOCALES.has(locale.split("-")[0]) : false;
}

/** Text direction (`"rtl"` | `"ltr"`) for the given locale. */
export function dirForLocale(locale: string | undefined | null): "rtl" | "ltr" {
  return isRtlLocale(locale) ? "rtl" : "ltr";
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        common: commonEn,
        auth: authEn,
        nav: navEn,
        inventory: inventoryEn,
        cards: cardsEn,
        reports: reportsEn,
        admin: adminEn,
        bpm: bpmEn,
        ppm: ppmEn,
        diagrams: diagramsEn,
        delivery: deliveryEn,
        grc: grcEn,
        notifications: notificationsEn,
        validation: validationEn,
        adm: admEn,
      },
    },
    fallbackLng: "en",
    returnEmptyString: false, // treat "" as missing → fall back to English
    defaultNS: "common",
    interpolation: {
      escapeValue: false, // React already escapes
    },
    detection: {
      order: ["localStorage"],
      caches: ["localStorage"],
      lookupLocalStorage: "turboea-locale",
    },
  });

/**
 * Languages bundled with the app shell. English is the fallback for every
 * missing key, so it is always present; any other language is a separate
 * chunk fetched by {@link loadLanguage} — an English session never downloads
 * or parses the Arabic strings.
 */
const LOADERS: Partial<Record<SupportedLocale, () => Promise<Record<string, Record<string, unknown>>>>> =
  {
    ar: () => import("./arResources").then((m) => m.default),
  };
const loaded = new Set<string>(["en"]);
const inflight = new Map<string, Promise<void>>();

function baseLocale(locale: string | undefined | null): string {
  return (locale ?? "en").split("-")[0];
}

/**
 * Make a language's strings available. Resolves at once for English or a
 * language already loaded; concurrent calls share one request. An unknown
 * language resolves without loading anything (English covers it).
 */
export function loadLanguage(locale: string | undefined | null): Promise<void> {
  const lng = baseLocale(locale);
  if (loaded.has(lng)) return Promise.resolve();
  const loader = LOADERS[lng as SupportedLocale];
  if (!loader) return Promise.resolve();
  let pending = inflight.get(lng);
  if (!pending) {
    pending = loader()
      .then((bundles) => {
        for (const [ns, data] of Object.entries(bundles)) {
          i18n.addResourceBundle(lng, ns, data, true, true);
        }
        loaded.add(lng);
      })
      .finally(() => inflight.delete(lng));
    inflight.set(lng, pending);
  }
  return pending;
}

/**
 * Switch the UI language once its strings are loaded, so the screen never
 * shows English keys mid-switch. Use instead of `i18n.changeLanguage`.
 */
export async function changeLanguage(locale: string): Promise<void> {
  await loadLanguage(locale);
  await i18n.changeLanguage(locale);
}

export default i18n;

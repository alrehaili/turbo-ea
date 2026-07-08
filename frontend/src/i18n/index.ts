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

// Arabic
import commonAr from "./locales/ar/common.json";
import authAr from "./locales/ar/auth.json";
import navAr from "./locales/ar/nav.json";
import inventoryAr from "./locales/ar/inventory.json";
import cardsAr from "./locales/ar/cards.json";
import reportsAr from "./locales/ar/reports.json";
import adminAr from "./locales/ar/admin.json";
import bpmAr from "./locales/ar/bpm.json";
import ppmAr from "./locales/ar/ppm.json";
import diagramsAr from "./locales/ar/diagrams.json";
import deliveryAr from "./locales/ar/delivery.json";
import grcAr from "./locales/ar/grc.json";
import notificationsAr from "./locales/ar/notifications.json";
import validationAr from "./locales/ar/validation.json";
import admAr from "./locales/ar/adm.json";

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
      ar: {
        common: commonAr,
        auth: authAr,
        nav: navAr,
        inventory: inventoryAr,
        cards: cardsAr,
        reports: reportsAr,
        admin: adminAr,
        bpm: bpmAr,
        ppm: ppmAr,
        diagrams: diagramsAr,
        delivery: deliveryAr,
        grc: grcAr,
        notifications: notificationsAr,
        validation: validationAr,
        adm: admAr,
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

export default i18n;

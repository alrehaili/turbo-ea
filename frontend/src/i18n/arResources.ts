/**
 * Arabic UI strings, loaded on demand by `loadLanguage("ar")` (`./index.ts`)
 * so English-only sessions never download or parse them.
 *
 * [FORK]
 */
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

const ar: Record<string, Record<string, unknown>> = {
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
};

export default ar;

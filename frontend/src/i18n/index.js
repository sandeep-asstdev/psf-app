/**
 * ============================================================================
 * FILE PURPOSE: Internationalization & Localization Configuration.
 * Configures multi-language translation strings and formatting helpers.
 * 
 * KEY RESPONSIBILITIES:
 * - Provides language dictionary mapping.
 * - Supports localized date and currency formatting.
 * 
 * COMMON ERRORS & TROUBLESHOOTING GUIDE:
 * - Error: Translation key shows instead of text
 *   -> Cause: The translation key was not defined in the active language dictionary.
 *   -> What should you do: Add the translation string to the dictionary.
 * ============================================================================
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      app: {
        title: "PSF - Post Service Follow-up",
        subtitle: "Automotive Dealership CRM & Follow-up Suite",
      },
      nav: {
        home: "Home",
        psfDashboard: "PSF Dashboard",
        happiness: "Happiness Calling",
        complaints: "Complaints",
        reports: "Reports",
        importData: "Data Import",
        users: "User Management",
        settings: "Settings",
        logout: "Log Out",
        login: "Log In",
      },
      common: {
        loading: "Loading...",
        search: "Search...",
        save: "Save",
        cancel: "Cancel",
        actions: "Actions",
        status: "Status",
        branch: "Branch",
        brand: "Brand",
      }
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;


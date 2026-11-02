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

export type SupportedLanguage = 'ko' | 'en' | 'zh' | 'ja';

export type TranslationDictionary = {
  nav: {
    homework: string;
    notices: string;
    materials: string;
    qa: string;
    exam: string;
    contest: string;
    collab: string;
    profile: string;
    admin: string;
    login: string;
    logout: string;
    dashboard: string;
    notifications: string;
  };
  home: {
    welcome: string;
    subWelcome: string;
    homeworksTitle: string;
    homeworksDesc: string;
    noticesTitle: string;
    noticesDesc: string;
    profileTitle: string;
    profileDesc: string;
    materialsTitle: string;
    materialsDesc: string;
    recentActivity: string;
    signInPrompt: string;
    signInBtn: string;
    goToFullDashboard: string;
    noRecentActivity: string;
    viewHomeworks: string;
  };
  common: {
    language: string;
    loading: string;
    submit: string;
    save: string;
    cancel: string;
    status: string;
    search: string;
  };
};

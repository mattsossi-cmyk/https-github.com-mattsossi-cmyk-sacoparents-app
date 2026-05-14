import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.bsossi.sacoparents",
  appName: "SA Coparents",
  webDir: "build",
  // Hide native splash on app load — we control reveal from JS
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      launchAutoHide: true,
      backgroundColor: "#FDFAF3",
      androidScaleType: "CENTER_CROP",
      showSpinner: false,
      splashFullScreen: true,
      splashImmersive: true,
    },
    StatusBar: {
      backgroundColor: "#FDFAF3",
      style: "DEFAULT",
      overlaysWebView: false,
    },
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
  },
  ios: {
    contentInset: "always",
    backgroundColor: "#FDFAF3",
  },
  android: {
    backgroundColor: "#FDFAF3",
  },
};

export default config;

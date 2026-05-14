/* Native-only helpers — gracefully no-op on the web.
   On the web, isNativePlatform() === false everywhere. */
import { Capacitor } from "@capacitor/core";

export const isNative = () => Capacitor.isNativePlatform();

let _biometricAvailable: boolean | null = null;

export async function isBiometricAvailable(): Promise<boolean> {
  if (!isNative()) return false;
  if (_biometricAvailable !== null) return _biometricAvailable;
  try {
    const { NativeBiometric } = await import("capacitor-native-biometric");
    const result = await NativeBiometric.isAvailable();
    _biometricAvailable = !!result.isAvailable;
    return _biometricAvailable;
  } catch {
    _biometricAvailable = false;
    return false;
  }
}

export async function requireBiometric(reason = "Unlock SA Coparents"): Promise<boolean> {
  if (!isNative()) return true; // no gate on web
  if (!(await isBiometricAvailable())) return true;
  try {
    const { NativeBiometric } = await import("capacitor-native-biometric");
    await NativeBiometric.verifyIdentity({
      reason,
      title: "SA Coparents",
      subtitle: "Use Face ID or Touch ID to continue",
      description: "",
    });
    return true;
  } catch {
    return false;
  }
}

/* Push notifications — registers the device with iOS/Android.
   Posts the token to the backend so it can send mediation reminders later. */
export async function registerPushNotifications(api: any): Promise<void> {
  if (!isNative()) return;
  try {
    const { PushNotifications } = await import("@capacitor/push-notifications");
    const perm = await PushNotifications.requestPermissions();
    if (perm.receive !== "granted") return;
    await PushNotifications.register();
    PushNotifications.addListener("registration", async (token) => {
      try {
        await api.post("/mediation/devices/register", {
          token: token.value,
          platform: Capacitor.getPlatform(),
        });
      } catch {
        /* non-fatal */
      }
    });
  } catch {
    /* Plugin not available — running on the web, ignore */
  }
}

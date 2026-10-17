// Get help page wording in English and Spanish. Local services are shown as admins typed them.
export const HELP_COPY = {
  en: {
    switchTo: "Español",
    switchLabel: "Ver esta página en español",
    title: "Get help",
    subtitle: "Free, confidential help is available any time.",
    danger: "In danger right now",
    call911: "Call 911",
    hotline: "National Domestic Violence Hotline",
    hotlineSub: "24/7, free and confidential.",
    textLine: "Text START to 88788",
    local: "Local services",
    chooseState: "Choose your state",
    selectState: "Select a state",
    website: "Website",
    noLocal: (state) => `No local services are listed for ${state} yet. The National Domestic Violence Hotline can connect you with help near you.`,
    guideTitle: "Keeping your device and account private",
    guide: [
      "Use a phone, computer and email account that only you can get into. Change passwords someone else might know.",
      "Turn off location sharing you don't need, and check which apps and people can see where you are.",
      "Look for linked devices, email forwarding rules or recovery numbers you don't recognize.",
      "Sign out when you're done, especially on a shared device.",
      "Your browser keeps a history. Use a private window, or clear your history if that's safe for you.",
      "Quick exit opens the calendar right away, and Back won't bring you here.",
    ],
    more: "More hotlines and resources",
    quickExit: "Quick exit",
  },
  es: {
    switchTo: "English",
    switchLabel: "View this page in English",
    title: "Obtener ayuda",
    subtitle: "Hay ayuda gratuita y confidencial disponible en cualquier momento.",
    danger: "Si está en peligro ahora",
    call911: "Llame al 911",
    hotline: "Línea Nacional sobre la Violencia Doméstica",
    hotlineSub: "Las 24 horas, todos los días. Gratuita y confidencial. Atención en español.",
    textLine: "Envíe START al 88788",
    local: "Servicios locales",
    chooseState: "Elija su estado",
    selectState: "Seleccione un estado",
    website: "Sitio web",
    noLocal: (state) => `Todavía no hay servicios locales para ${state}. La Línea Nacional sobre la Violencia Doméstica puede ponerle en contacto con ayuda cerca de usted.`,
    guideTitle: "Cómo mantener privados su dispositivo y sus cuentas",
    guide: [
      "Use un teléfono, una computadora y una cuenta de correo a los que solo usted pueda entrar. Cambie las contraseñas que otra persona pueda conocer.",
      "Desactive la ubicación compartida que no necesite y revise qué aplicaciones y personas pueden ver dónde está.",
      "Busque dispositivos vinculados, reglas de reenvío de correo o números de recuperación que no reconozca.",
      "Cierre la sesión cuando termine, sobre todo en un dispositivo compartido.",
      "Su navegador guarda un historial. Use una ventana privada o borre el historial si es seguro para usted.",
      "Salida rápida abre el calendario de inmediato, y el botón Atrás no le traerá de vuelta aquí.",
    ],
    more: "Más líneas de ayuda y recursos (en inglés)",
    quickExit: "Salida rápida",
  },
};

const KEY = "sac_lang";

export function initialHelpLang() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "en" || saved === "es") return saved;
  } catch {
    /* storage unavailable */
  }
  return (navigator.language || "").toLowerCase().startsWith("es") ? "es" : "en";
}

export function saveHelpLang(lang) {
  try {
    localStorage.setItem(KEY, lang);
  } catch {
    /* storage unavailable */
  }
}

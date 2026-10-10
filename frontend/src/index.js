import React from "react";
import ReactDOM from "react-dom/client";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register the service worker for offline support + PWA install.
// Only runs in production builds — avoids interfering with dev hot-reload.
if (
  "serviceWorker" in navigator &&
  (window.location.hostname !== "localhost" ||
    process.env.NODE_ENV === "production")
) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .catch((err) => {
        // Silent — offline support is a progressive enhancement
        console.warn("SW registration failed:", err);
      });
  });
}

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
// IBM Plex, bundled locally via @fontsource — the venue build must need
// no network for fonts (offline demo, ADR-005 spirit). Three voices:
// Sans for UI, Mono for data, Serif for the analyst narration.
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-serif/400.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

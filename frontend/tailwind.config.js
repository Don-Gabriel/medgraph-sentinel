/** @type {import('tailwindcss').Config} */
// Design tokens for the investigator console. Thesis: calm ink chrome,
// severity rendered as a single-family "heat ramp" (ember -> amber -> ash,
// deliberately not a traffic light), one teal "tracer" hue reserved for
// interaction, and all visual drama reserved for implicated nodes in the
// evidence graph. Never scatter raw hex outside this file / graphStyle.js.
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0A0D13", // app canvas
          900: "#10141C", // panels
          850: "#141A24", // raised rows / inputs
          800: "#1A2130", // hover surfaces
          700: "#232B3A", // hairlines & borders
        },
        paper: {
          DEFAULT: "#E7E4DC", // primary text (warm, not pure white)
          mut: "#8B94A6", // secondary text
          dim: "#5D6678", // tertiary text / disabled
        },
        heat: {
          high: "#FF6A3D", // ember — burning
          med: "#E3A455", // amber — glowing
          low: "#97907F", // ash — noted, not burning
        },
        tracer: {
          DEFAULT: "#57C4B8", // interaction only: focus, links, reviewed
          dim: "#2E6B64",
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
        serif: ['"IBM Plex Serif"', "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};

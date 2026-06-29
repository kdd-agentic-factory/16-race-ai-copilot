/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        kdd: {
          base: "#0B0D12",
          surface: "#111318",
          card: "#181C24",
          hover: "#1E2330",
          accent: "#E03737",
          green: "#22C55E",
          yellow: "#F59E0B",
          blue: "#3B82F6",
          orange: "#F97316",
          cyan: "#00B7FF",
          text: "#E6EAF4",
          dim: "#8B92A8",
          muted: "#757E92",
        },
      },
      fontFamily: {
        display: ["Barlow Condensed", "Rajdhani", "system-ui", "sans-serif"],
        sans: ["Barlow", "Rajdhani", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "monospace"],
      },
      borderRadius: {
        kdd: "6px",
        "kdd-lg": "10px",
      },
    },
  },
  plugins: [],
}

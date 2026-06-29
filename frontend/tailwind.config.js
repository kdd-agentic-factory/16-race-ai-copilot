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
        // Override default zinc palette to align with KDD design system
        // so all existing zinc-* classes map to the canonical tokens
        zinc: {
          50:   "#F4F5F7",
          100:  "#E6EAF4",
          200:  "#E6EAF4",
          300:  "#E6EAF4",
          400:  "#8B92A8",
          500:  "#8B92A8",
          600:  "#757E92",
          700:  "#1E2330",
          800:  "#111318",
          900:  "#181C24",
          950:  "#0B0D12",
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

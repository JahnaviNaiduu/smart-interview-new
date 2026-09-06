import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        glass: {
          bg: "rgba(255,255,255,0.04)",
          "bg-hover": "rgba(255,255,255,0.08)",
          border: "rgba(255,255,255,0.10)",
          "border-strong": "rgba(255,255,255,0.20)",
        },
      },
      backdropBlur: {
        glass: "12px",
      },
      boxShadow: {
        glass: "0 0 20px rgba(255,255,255,0.05)",
        "glass-strong": "0 0 40px rgba(255,255,255,0.10)",
        "glow-white": "0 0 30px rgba(255,255,255,0.15)",
      },
    },
  },
  plugins: [],
};

export default config;

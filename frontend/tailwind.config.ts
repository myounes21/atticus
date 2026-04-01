import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";
import containerQueries from "@tailwindcss/container-queries";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#005f5a",
        "primary-alt": "#0d7a74",
        "primary-fixed": "#99f2ea",
        surface: "#f6faf9",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f0f4f3",
        "surface-container": "#ebefee",
        "surface-container-high": "#e5e9e8",
        "on-surface": "#181c1c",
        "on-surface-variant": "#3e4948",
        outline: "#6e7978",
        "outline-variant": "#bdc9c7",
        tertiary: "#395b56",
      },
      fontFamily: {
        display: ["var(--font-manrope)", "sans-serif"],
        headline: ["var(--font-manrope)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        label: ["var(--font-inter)", "sans-serif"],
      },
    },
  },
  plugins: [forms, containerQueries],
};

export default config;

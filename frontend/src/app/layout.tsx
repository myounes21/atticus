import "./globals.css";
import type { ReactNode } from "react";
import { Inter, Manrope } from "next/font/google";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${inter.variable} font-body selection:bg-primary-fixed selection:text-on-surface`}>
        {children}
      </body>
    </html>
  );
}

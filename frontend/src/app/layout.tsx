import type { Metadata } from "next";
import "@fontsource-variable/bodoni-moda/standard.css";
import "@fontsource-variable/source-sans-3/wght.css";
import "@fontsource-variable/source-sans-3/wght-italic.css";
import "./globals.css";
import TopNavigation from "@/components/layout/top-navigation";

export const metadata: Metadata = {
  title: "SENTINEL · Your Data Center",
  description: "Detect. Decide. Defend. Infrastructure monitoring command center.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><a href="#main" className="skip-link">Skip to content</a><TopNavigation />{children}</body></html>;
}

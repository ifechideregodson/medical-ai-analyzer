import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedAI Clinical Analyzer",
  description: "Medical imaging research and clinical decision-support platform",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: "CoverWise AI — Policy-to-Patient Insurance Coverage & Cost Intelligence",
  description:
    "Intelligent insurance policy analysis providing deterministic cost breakdowns, potential coverage insights, and patient responsibility estimates.",
  keywords: [
    "health insurance",
    "policy analysis",
    "coverage intelligence",
    "treatment cost estimate",
    "deductible calculator",
    "out of pocket cost",
  ],
  authors: [{ name: "CoverWise AI Team" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#F8F9FF] text-[#0A1D2E] antialiased selection:bg-[#EEF4FF] selection:text-[#0052D1]">
        {children}
      </body>
    </html>
  );
}

import type { Metadata, Viewport } from "next";
import { Fraunces, Outfit } from "next/font/google";
import { Navbar } from "@/components/Navbar";
import { SiteFooter } from "@/components/SiteFooter";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Travel Eye",
    template: "%s · Travel Eye",
  },
  description:
    "Point your camera at a historic place and read the story written for it.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "Travel Eye",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#143028",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${outfit.variable} ${fraunces.variable} h-full`}>
      <body className="flex min-h-full flex-col antialiased">
        <a href="#content" className="skip-link">
          Skip to content
        </a>
        <Navbar />
        <main id="content" className="flex-1">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}

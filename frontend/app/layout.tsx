import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FreeFood UCD - Never Miss Free Food on Campus",
  description: "Get instant notifications when UCD societies post about free food events. Never miss free pizza again!",
  keywords: ["UCD", "free food", "university", "students", "events", "pizza"],
  authors: [{ name: "FreeFood UCD" }],
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/apple-icon.png",
  },
  openGraph: {
    title: "FreeFood UCD",
    description: "Never miss free food on campus",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

// Made with Bob

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { MainNav } from "@/components/layout/main-nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Real Estate Assistant",
  description: "Next-gen real estate search and analytics",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col`}
      >
        <header className="border-b">
          <div className="flex h-16 items-center px-4 container mx-auto">
             <div className="font-bold text-xl mr-4 hidden md:block">AI Estate</div>
             <MainNav />
          </div>
        </header>
        <main className="flex-1">
          {children}
        </main>
      </body>
    </html>
  );
}

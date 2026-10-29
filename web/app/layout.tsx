import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { LangProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "priceintel — what did the public sector pay?",
  description: "Hybrid retrieval, an LLM judge and robust statistics over (synthetic) public purchase records.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <LangProvider>
          <div className="shell">
            <Nav />
            {children}
          </div>
        </LangProvider>
      </body>
    </html>
  );
}

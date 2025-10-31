import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Document Chat Assistant - Overheid",
  description: "Ask questions about your uploaded documents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="nl" suppressHydrationWarning>
      <body className="antialiased" style={{ fontFamily: 'Verdana, sans-serif' }}>
        {children}
      </body>
    </html>
  );
}

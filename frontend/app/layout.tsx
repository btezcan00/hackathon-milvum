import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WooWijzer",
  description: "happy halloween, woooooo",
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

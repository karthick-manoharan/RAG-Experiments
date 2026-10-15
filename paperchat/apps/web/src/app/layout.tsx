import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperChat",
  description: "Explore Attention Is All You Need with streamed, source-grounded answers.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}

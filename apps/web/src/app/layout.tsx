import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "N55 Intelligence Lab",
  description: "Vehicle Intelligence Platform — fundação de engenharia",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}

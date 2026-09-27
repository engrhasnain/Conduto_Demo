import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ChatProvider } from "@/components/chat/ChatProvider";
import { AppProvider } from "@/components/providers";
import Shell from "@/components/Shell";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Conduto · Project Intelligence (demo)",
  description: "Consolidated project control and profitability intelligence for pipeline and civil-works projects. Demo with synthetic data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" translate="no" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <AppProvider>
          <ChatProvider>
            <Shell>{children}</Shell>
          </ChatProvider>
        </AppProvider>
      </body>
    </html>
  );
}

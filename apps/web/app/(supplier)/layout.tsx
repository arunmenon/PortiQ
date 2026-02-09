"use client";

import { SupplierSidebar } from "@/components/supplier/supplier-sidebar";
import { Header } from "@/components/layout/header";
import { CommandBar } from "@/components/command-bar";

export default function SupplierLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <SupplierSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
      <CommandBar />
    </div>
  );
}

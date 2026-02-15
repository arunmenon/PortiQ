"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Package,
  FolderTree,
  Search,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Anchor,
  Users,
  FileText,
  ShoppingCart,
  Truck,
  Receipt,
  AlertTriangle,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const navigation = [
  { name: "PortiQ Chat", href: "/chat", icon: Sparkles },
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Products", href: "/products", icon: Package },
  { name: "Categories", href: "/categories", icon: FolderTree },
  { name: "Search", href: "/search", icon: Search },
  { name: "Suppliers", href: "/suppliers", icon: Users },
  { name: "RFQs", href: "/rfqs", icon: FileText },
  { name: "Orders", href: "/orders", icon: ShoppingCart },
  { name: "Deliveries", href: "/deliveries", icon: Truck },
  { name: "Invoices", href: "/invoices", icon: Receipt },
  { name: "Disputes", href: "/disputes", icon: AlertTriangle },
  { name: "Settlements", href: "/settlements", icon: Wallet },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r bg-card transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex h-14 items-center px-4">
        <Link href="/" className="flex items-center gap-2">
          <Anchor className="h-6 w-6 text-primary" />
          {!collapsed && (
            <span className="text-lg font-bold text-foreground">PortiQ</span>
          )}
        </Link>
      </div>

      <Separator />

      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href ||
                pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
              title={collapsed ? item.name : undefined}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <Separator />

      <div className="p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}

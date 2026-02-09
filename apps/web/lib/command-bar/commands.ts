import {
  LayoutDashboard,
  Package,
  FolderTree,
  Search,
  Sparkles,
  Plus,
  Download,
  Users,
  FileText,
  ShoppingCart,
  type LucideIcon,
} from "lucide-react";

export interface CommandItem {
  id: string;
  label: string;
  icon: LucideIcon;
  group: "navigation" | "actions";
  shortcut?: string;
  keywords?: string[];
  onSelect: () => void;
}

export function getNavigationCommands(push: (path: string) => void): CommandItem[] {
  return [
    {
      id: "nav-dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      group: "navigation",
      shortcut: "G D",
      keywords: ["home", "overview"],
      onSelect: () => push("/"),
    },
    {
      id: "nav-products",
      label: "Products",
      icon: Package,
      group: "navigation",
      shortcut: "G P",
      keywords: ["catalog", "items"],
      onSelect: () => push("/products"),
    },
    {
      id: "nav-categories",
      label: "Categories",
      icon: FolderTree,
      group: "navigation",
      shortcut: "G C",
      keywords: ["tree", "groups"],
      onSelect: () => push("/categories"),
    },
    {
      id: "nav-search",
      label: "Search",
      icon: Search,
      group: "navigation",
      shortcut: "G S",
      keywords: ["find", "lookup"],
      onSelect: () => push("/search"),
    },
    {
      id: "nav-chat",
      label: "PortiQ Chat",
      icon: Sparkles,
      group: "navigation",
      keywords: ["ai", "assistant", "help"],
      onSelect: () => push("/chat"),
    },
    {
      id: "nav-suppliers",
      label: "Suppliers",
      icon: Users,
      group: "navigation",
      shortcut: "G U",
      keywords: ["vendor", "supplier", "onboarding"],
      onSelect: () => push("/suppliers"),
    },
    {
      id: "nav-rfqs",
      label: "RFQs",
      icon: FileText,
      group: "navigation",
      keywords: ["quote", "request"],
      onSelect: () => push("/rfqs"),
    },
    {
      id: "nav-orders",
      label: "Orders",
      icon: ShoppingCart,
      group: "navigation",
      keywords: ["purchase", "order", "delivery"],
      onSelect: () => push("/orders"),
    },
  ];
}

export function getActionCommands(push: (path: string) => void): CommandItem[] {
  return [
    {
      id: "action-add-product",
      label: "Add Product",
      icon: Plus,
      group: "actions",
      keywords: ["create", "new", "product"],
      onSelect: () => push("/products?action=create"),
    },
    {
      id: "action-create-rfq",
      label: "Create RFQ",
      icon: FileText,
      group: "actions",
      keywords: ["new", "rfq", "request", "quote", "procurement"],
      onSelect: () => push("/rfqs/create"),
    },
    {
      id: "action-export-catalog",
      label: "Export Catalog",
      icon: Download,
      group: "actions",
      keywords: ["download", "csv", "export"],
      onSelect: () => push("/products?action=export"),
    },
  ];
}

export function filterCommands(commands: CommandItem[], query: string): CommandItem[] {
  if (!query) return commands;
  const lower = query.toLowerCase();
  return commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(lower) ||
      cmd.keywords?.some((kw) => kw.includes(lower))
  );
}

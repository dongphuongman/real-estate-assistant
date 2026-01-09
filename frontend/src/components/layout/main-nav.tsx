"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Building2, Search, BarChart3, MessageSquare } from "lucide-react";

export function MainNav() {
  const pathname = usePathname();

  const routes = [
    {
      href: "/",
      label: "Home",
      icon: Building2,
      active: pathname === "/",
    },
    {
      href: "/search",
      label: "Search",
      icon: Search,
      active: pathname === "/search",
    },
    {
      href: "/chat",
      label: "Assistant",
      icon: MessageSquare,
      active: pathname === "/chat",
    },
    {
      href: "/analytics",
      label: "Analytics",
      icon: BarChart3,
      active: pathname === "/analytics",
    },
  ];

  return (
    <nav className="flex items-center space-x-6 lg:space-x-8 mx-6">
      {routes.map((route) => (
        <Link
          key={route.href}
          href={route.href}
          className={cn(
            "text-sm font-medium transition-colors hover:text-primary flex items-center gap-x-2",
            route.active
              ? "text-black dark:text-white"
              : "text-muted-foreground"
          )}
        >
          <route.icon className="w-4 h-4" />
          {route.label}
        </Link>
      ))}
    </nav>
  );
}

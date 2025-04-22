"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Book, LayoutDashboard, LogOut, PenLine, Vocabulary } from "lucide-react";
import { createSupabaseClient } from "@/lib/supabase/client";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createSupabaseClient();

  async function handleSignOut() {
    const { error } = await supabase.auth.signOut();
    
    if (error) {
      toast({
        title: "Error signing out",
        description: error.message,
        variant: "destructive",
      });
      return;
    }
    
    router.push("/sign-in");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background">
      <div className="container flex h-16 items-center justify-between py-4">
        <div className="flex items-center gap-2">
          <Book className="h-6 w-6" />
          <Link href="/dashboard" className="text-lg font-semibold">
            LinguaLog
          </Link>
        </div>
        
        <nav className="hidden md:flex items-center gap-6">
          <Link 
            href="/dashboard" 
            className={`flex items-center gap-2 text-sm ${pathname === "/dashboard" ? "font-medium" : "text-muted-foreground"}`}
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Link>
          
          <Link 
            href="/entries/new" 
            className={`flex items-center gap-2 text-sm ${pathname === "/entries/new" ? "font-medium" : "text-muted-foreground"}`}
          >
            <PenLine className="h-4 w-4" />
            New Entry
          </Link>
          
          <Link 
            href="/vocabulary" 
            className={`flex items-center gap-2 text-sm ${pathname === "/vocabulary" ? "font-medium" : "text-muted-foreground"}`}
          >
            <Vocabulary className="h-4 w-4" />
            Vocabulary
          </Link>
          
          <Link 
            href="/stats" 
            className={`flex items-center gap-2 text-sm ${pathname === "/stats" ? "font-medium" : "text-muted-foreground"}`}
          >
            <LayoutDashboard className="h-4 w-4" />
            Stats
          </Link>
        </nav>
        
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={handleSignOut}>
            <LogOut className="h-4 w-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>
    </header>
  );
}
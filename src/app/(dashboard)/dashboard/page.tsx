import { Metadata } from "next";
import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EntryList } from "@/components/entries/entry-list";

export const metadata: Metadata = {
  title: "Dashboard | LinguaLog",
  description: "Manage your language learning journal entries",
};

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Your Journal</h1>
          <p className="text-muted-foreground">
            Track your language learning journey
          </p>
        </div>
        <Link href="/entries/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Entry
          </Button>
        </Link>
      </div>
      
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Recent Entries</h2>
        <EntryList />
      </div>
    </div>
  );
}
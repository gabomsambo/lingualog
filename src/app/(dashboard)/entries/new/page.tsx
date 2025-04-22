import { Metadata } from "next";
import { NewEntryForm } from "@/components/entries/new-entry-form";

export const metadata: Metadata = {
  title: "New Entry | LinguaLog",
  description: "Create a new language learning journal entry",
};

export default function NewEntryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">New Journal Entry</h1>
        <p className="text-muted-foreground">
          Write your thoughts, practice your language skills
        </p>
      </div>
      
      <NewEntryForm />
    </div>
  );
}
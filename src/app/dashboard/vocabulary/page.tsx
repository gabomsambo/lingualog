import { Metadata } from "next";
import { VocabularyList } from "@/components/vocabulary/vocabulary-list";

export const metadata: Metadata = {
  title: "Vocabulary | LinguaLog",
  description: "View your saved vocabulary words from your journal entries",
};

export default function VocabularyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Your Vocabulary</h1>
        <p className="text-muted-foreground">
          Words extracted from your journal entries
        </p>
      </div>
      
      <VocabularyList />
    </div>
  );
}
import { StatsOverview } from "@/components/stats/stats-overview";
import { WritingProgress } from "@/components/stats/writing-progress";
import { LanguageDistribution } from "@/components/stats/language-distribution";

export const metadata = {
  title: "Stats | LinguaLog",
  description: "Track your language learning progress and writing statistics",
};

export default function StatsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Writing Statistics</h1>
        <p className="text-muted-foreground">
          Track your language learning progress
        </p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <StatsOverview />
      </div>
      
      <div className="grid gap-6 md:grid-cols-2">
        <WritingProgress />
        <LanguageDistribution />
      </div>
    </div>
  );
}
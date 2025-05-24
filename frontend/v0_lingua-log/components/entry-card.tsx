import Link from "next/link"
import { BookOpen, Trash2 } from "lucide-react"

import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/utils"

// Badge variants for languages
const languageBadgeVariants: Record<string, "blue" | "pink" | "purple" | "green" | "yellow" | "default" | "outline"> = {
  Japanese: "blue",
  Spanish: "pink",
  French: "purple",
  German: "green",
  Italian: "yellow",
  Korean: "purple",
  English: "yellow",
  Other: "default",
}

interface EntryCardProps {
  entry: {
    id: string
    title: string
    language?: string
    languageEmoji: string
    date?: string
    excerpt: string
  }
  onDelete: (entryId: string) => void;
}

export function EntryCard({ entry, onDelete }: EntryCardProps) {
  const badgeVariant = languageBadgeVariants[entry.language || "Other"] || "default"

  return (
    <Card className="fun-card group relative border-fun-purple/20 hover:border-fun-purple/40 h-full flex flex-col transition-all duration-300 hover:shadow-lg">
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <Button
          variant="ghost"
          size="icon"
          className="text-red-500 hover:bg-red-100 dark:hover:bg-red-900/50 rounded-full h-8 w-8"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(entry.id);
          }}
          title="Delete Entry"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
      <Link href={`/entries/${entry.id}`} className="block h-full">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-3">
            <h3 className="text-xl font-bold group-hover:text-fun-purple transition-colors duration-300">
              {entry.title}
            </h3>
            <div className="flex items-center gap-3">
              {entry.language && entry.languageEmoji && (
                <Badge variant={badgeVariant} className="text-sm">
                  <span className="mr-1">{entry.languageEmoji}</span> {entry.language}
                </Badge>
              )}
              {entry.date && (
                <span className="text-sm text-muted-foreground">{formatDate(entry.date)}</span>
              )}
            </div>
          </div>
          <p className="text-muted-foreground line-clamp-2 font-serif">{entry.excerpt}</p>
        </CardContent>
        <CardFooter className="px-6 pb-6 pt-0">
          <Button
            variant="outline"
            className="rounded-full border-fun-purple/30 hover:border-fun-purple/50 hover:bg-fun-purple/5"
          >
            <BookOpen className="mr-2 h-4 w-4" />
            Read Entry
          </Button>
        </CardFooter>
      </Link>
    </Card>
  )
}

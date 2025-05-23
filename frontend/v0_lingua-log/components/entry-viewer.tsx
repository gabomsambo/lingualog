import { formatDate } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface EntryViewerProps {
  entry: {
    title: string
    language: string
    languageEmoji: string
    date: string
    content: string
  }
}

export function EntryViewer({ entry }: EntryViewerProps) {
  return (
    <Card className="border-fun-purple/20 shadow-fun rounded-3xl overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-fun-purple/10 to-fun-pink/10 pb-4">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
          <CardTitle className="text-2xl">
            <span className="fun-heading">Your Journal Entry: {entry.title}</span>
          </CardTitle>
          <Badge variant="purple" className="text-base px-4 py-1 h-8">
            <span className="mr-2">{entry.languageEmoji}</span> {entry.language}
          </Badge>
        </div>
        <p className="text-muted-foreground text-base">Written on {formatDate(entry.date)}</p>
      </CardHeader>
      <CardContent className="p-6">
        <div className="prose max-w-none text-lg font-serif">
          {entry.content.split("\n\n").map((paragraph, index) => (
            <p key={index} className="mb-4 leading-relaxed">
              {paragraph}
            </p>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

import { AlertCircle } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function WritingTips() {
  return (
    <Alert className="bg-fun-yellow/10 border-fun-yellow/30 rounded-xl">
      <AlertCircle className="h-5 w-5 text-fun-yellow" />
      <AlertTitle className="text-fun-yellow font-medium">Writing Tips</AlertTitle>
      <AlertDescription className="mt-2">
        <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
          <li>Don't worry about making mistakes - that's how we learn!</li>
          <li>Try to write about your day or something you're interested in</li>
          <li>Use new vocabulary words you've been learning</li>
          <li>If you get stuck, write simpler sentences - quality over quantity</li>
          <li>Have fun with it! Language learning should be enjoyable</li>
        </ul>
      </AlertDescription>
    </Alert>
  )
}

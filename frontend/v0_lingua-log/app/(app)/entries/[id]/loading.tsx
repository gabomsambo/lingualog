import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowLeft } from "lucide-react"
import { LoadingSpinner } from "@/components/loading-spinner"

export default function Loading() {
  return (
    <div className="container max-w-3xl mx-auto py-8 px-4">
      <div className="flex items-center space-x-4 mb-8">
        <Button variant="ghost" size="icon" className="rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <Skeleton className="h-10 w-64" />
      </div>

      <Card className="fun-card border-fun-purple/20">
        <CardHeader>
          <Skeleton className="h-10 w-3/4 mb-2" />
          <div className="flex justify-between">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-6 w-40" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-3/4" />
        </CardContent>
      </Card>

      <div className="flex justify-center py-8">
        <LoadingSpinner text="Loading your entry..." />
      </div>
    </div>
  )
}

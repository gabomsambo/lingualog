import type * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 shadow-md",
  {
    variants: {
      variant: {
        default: "badge-fun badge-purple",
        green: "badge-fun badge-green",
        blue: "badge-fun badge-blue",
        purple: "badge-fun badge-purple",
        pink: "badge-fun badge-pink",
        yellow: "badge-fun badge-yellow",
        outline: "border-2 border-fun-purple/50 bg-white text-fun-purple",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }

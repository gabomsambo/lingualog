import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 btn-fun",
  {
    variants: {
      variant: {
        default: "bg-fun-green text-white hover:bg-fun-green/90 rounded-full shadow-lg hover:shadow-xl",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-full shadow-lg hover:shadow-xl",
        outline:
          "border-2 border-fun-purple/30 bg-background hover:bg-fun-purple/10 hover:border-fun-purple/50 rounded-full shadow-md hover:shadow-lg",
        secondary: "bg-fun-purple text-white hover:bg-fun-purple/90 rounded-full shadow-lg hover:shadow-xl",
        ghost: "hover:bg-fun-purple/10 rounded-full",
        link: "text-fun-purple underline-offset-4 hover:underline",
        green: "bg-gradient-green-blue text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl",
        blue: "bg-gradient-blue-purple text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl",
        purple: "bg-gradient-purple-pink text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl",
        yellow: "bg-gradient-yellow-orange text-white hover:opacity-90 rounded-full shadow-lg hover:shadow-xl",
      },
      size: {
        default: "h-12 px-6 py-3",
        sm: "h-10 rounded-full px-4",
        lg: "h-14 rounded-full px-8 text-base",
        icon: "h-12 w-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return <Comp className={cn(buttonVariants({ variant, size, className }), "btn-bounce")} ref={ref} {...props} />
  },
)
Button.displayName = "Button"

export { Button, buttonVariants }

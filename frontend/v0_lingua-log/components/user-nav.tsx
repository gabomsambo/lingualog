"use client"

import { useRouter } from "next/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/components/ui/use-toast"
import { LogOut, Settings, User } from "lucide-react"
import { useState, useEffect } from "react"
import { getUserProfile, type UserProfile } from "@/lib/user-service"

export function UserNav() {
  const router = useRouter()
  const { toast } = useToast()
  const [showEmoji, setShowEmoji] = useState(false)
  const [userName, setUserName] = useState("User")
  const [userEmail, setUserEmail] = useState("user@example.com")
  const [userInitials, setUserInitials] = useState("U")

  useEffect(() => {
    async function loadProfile() {
      const profile = await getUserProfile();
      if (profile) {
        setUserName(profile.username || profile.email.split('@')[0] || "User");
        setUserEmail(profile.email || "user@example.com");
        const nameForInitials = profile.username || profile.email.split('@')[0];
        if (nameForInitials) {
          const parts = nameForInitials.split(' ');
          if (parts.length > 1) {
            setUserInitials(parts[0][0].toUpperCase() + parts[parts.length - 1][0].toUpperCase());
          } else if (parts[0] && parts[0].length > 0) {
            setUserInitials(parts[0][0].toUpperCase() + (parts[0].length > 1 ? parts[0][1].toUpperCase() : ''));
          } else {
            setUserInitials("U");
          }
        } else {
          setUserInitials("U");
        }
      }
    }
    loadProfile();
  }, []);

  const handleLogout = async () => {
    setShowEmoji(true)

    toast({
      title: "See you soon! 👋",
      description: "You have been logged out successfully",
      variant: "fun",
    })

    setTimeout(() => {
      router.push("/auth/sign-in")
    }, 1000)
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-12 w-12 rounded-full p-0">
          <Avatar className="h-12 w-12 ring-4 ring-fun-purple/30 transition-all duration-300 hover:ring-fun-purple/70">
            <AvatarImage src="/mystical-forest-spirit.png" alt="User avatar" />
            <AvatarFallback className="bg-gradient-to-br from-fun-blue to-fun-purple text-white text-lg">
              {userInitials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56 rounded-2xl" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-base font-medium leading-none">{userName}</p>
            <p className="text-sm leading-none text-muted-foreground">{userEmail}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem className="rounded-xl cursor-pointer text-base py-2">
            <User className="mr-2 h-5 w-5 text-fun-blue" />
            <span>Profile</span>
          </DropdownMenuItem>
          <DropdownMenuItem className="rounded-xl cursor-pointer text-base py-2">
            <Settings className="mr-2 h-5 w-5 text-fun-purple" />
            <span>Settings</span>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="rounded-xl cursor-pointer text-base py-2">
          <LogOut className="mr-2 h-5 w-5 text-fun-pink" />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

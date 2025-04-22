import { redirect } from "next/navigation";

export default function HomePage() {
  // Redirect to the sign-in page for now
  redirect("/sign-in");
}
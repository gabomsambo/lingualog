import { redirect } from "next/navigation";

export default function DashboardIndex() {
  // Redirect to the dashboard page
  redirect("/dashboard/dashboard");
}
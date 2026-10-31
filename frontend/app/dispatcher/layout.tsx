import RoleGuard from "@/components/RoleGuard";

// Dispatch belongs to the dispatcher; a team member is sent to the chat.
export default function DispatcherLayout({ children }: { children: React.ReactNode }) {
  return <RoleGuard allow={["dispatcher"]}>{children}</RoleGuard>;
}

import RoleGuard from "@/components/RoleGuard";

// The chat belongs to team members. The dispatcher reads it on the Dispatcher page and is sent there.
export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return <RoleGuard allow={["team"]}>{children}</RoleGuard>;
}

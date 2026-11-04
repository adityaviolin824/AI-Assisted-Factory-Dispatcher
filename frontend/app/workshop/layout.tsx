import RoleGuard from "@/components/RoleGuard";

// The Workshop page belongs to the workshops; anyone else is sent to their own page.
export default function WorkshopLayout({ children }: { children: React.ReactNode }) {
  return <RoleGuard allow={["workshop"]}>{children}</RoleGuard>;
}

import { useAuth } from "../app/auth";
import { SlowMailboxPage } from "../pages/SlowMailboxPage";
import { WorkspacePage } from "../pages/WorkspacePage";

export function RoleHome() {
  const { user } = useAuth();
  if (user?.role === "visitor") {
    return <SlowMailboxPage />;
  }
  return <WorkspacePage />;
}

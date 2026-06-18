import { Navigate } from "react-router-dom";

import { useAuth } from "../app/auth";

export function AuthGate({ children }: { children: JSX.Element }) {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

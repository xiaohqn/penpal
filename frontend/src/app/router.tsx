import { createBrowserRouter } from "react-router-dom";

import { AppProviders } from "./providers";
import { AuthGate } from "../components/AuthGate";
import { RoleHome } from "../components/RoleHome";
import { LoginPage } from "../pages/LoginPage";
import { RecordsPage } from "../pages/RecordsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AppProviders>
        <AuthGate>
          <RoleHome />
        </AuthGate>
      </AppProviders>
    ),
  },
  {
    path: "/login",
    element: (
      <AppProviders>
        <LoginPage />
      </AppProviders>
    ),
  },
  {
    path: "/records",
    element: (
      <AppProviders>
        <AuthGate>
          <RecordsPage />
        </AuthGate>
      </AppProviders>
    ),
  },
]);

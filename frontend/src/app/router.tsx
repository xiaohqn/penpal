import { createBrowserRouter } from "react-router-dom";

import { AppProviders } from "./providers";
import { RecordsPage } from "../pages/RecordsPage";
import { WorkspacePage } from "../pages/WorkspacePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AppProviders>
        <WorkspacePage />
      </AppProviders>
    ),
  },
  {
    path: "/records",
    element: (
      <AppProviders>
        <RecordsPage />
      </AppProviders>
    ),
  },
]);

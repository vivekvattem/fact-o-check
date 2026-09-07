import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "./layouts/AppLayout";
import { DocumentDetailPage } from "./pages/DocumentDetailPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { FactsPage } from "./pages/FactsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RelationshipsPage } from "./pages/RelationshipsPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "documents/:documentId", element: <DocumentDetailPage /> },
      { path: "facts", element: <FactsPage /> },
      { path: "relationships", element: <RelationshipsPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}

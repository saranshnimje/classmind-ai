import { Compass, Home } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState, PageHeader } from "../components/ui";
import { useDocumentTitle } from "../lib/hooks";

export function NotFoundPage() {
  useDocumentTitle("Page not found");

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="404"
        title="Page not found"
        description="The page you requested does not exist in this local workspace."
      />
      <EmptyState
        icon={Compass}
        title="Nothing here"
        description="Check the address, or return to the dashboard to continue reviewing sessions."
        action={
          <Link to="/" className="btn btn-primary">
            <Home className="h-4 w-4" /> Back to dashboard
          </Link>
        }
      />
    </div>
  );
}

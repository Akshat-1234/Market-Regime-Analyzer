import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="empty-state">
      <h2>Page not found</h2>
      <p>The page you're looking for doesn't exist.</p>
      <Link className="ghost-button" to="/">
        Back to Strategy Lab <span>↗</span>
      </Link>
    </div>
  );
}

import { Link } from "react-router-dom";
export default function NotFoundPage() {
  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold mb-4">404</h1>
      <p className="text-gray-500 mb-6">Page not found.</p>
      <Link to="/" className="btn-primary">Go home</Link>
    </div>
  );
}

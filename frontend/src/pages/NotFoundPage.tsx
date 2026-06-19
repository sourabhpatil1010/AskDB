import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Home, ArrowLeft, Search } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center max-w-md"
      >
        <div className="text-8xl font-bold bg-gradient-to-br from-primary to-violet-400 bg-clip-text text-transparent mb-4">
          404
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-3">Page not found</h2>
        <p className="text-muted-foreground mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 transition-colors"
          >
            <Home className="w-4 h-4" />
            Dashboard
          </Link>
          <Link
            to="/search"
            className="flex items-center gap-2 px-5 py-2.5 bg-card border border-border text-foreground text-sm font-medium rounded-xl hover:bg-muted/50 transition-colors"
          >
            <Search className="w-4 h-4" />
            AI Search
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

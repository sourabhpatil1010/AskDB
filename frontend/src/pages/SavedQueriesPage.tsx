import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bookmark,
  Search,
  Star,
  Trash2,
  Play,
  Edit3,
  Check,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAppStore } from "@/store/appStore";
import { formatDate } from "@/lib/utils";

export default function SavedQueriesPage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const { savedQueries, removeSavedQuery, toggleFavoriteQuery, updateSavedQuery } =
    useAppStore();

  const filteredQueries = savedQueries.filter((q) =>
    q.query.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleEdit = (id: string, currentQuery: string) => {
    setEditingId(id);
    setEditText(currentQuery);
  };

  const handleSaveEdit = (id: string) => {
    if (editText.trim()) {
      updateSavedQuery(id, { query: editText.trim() });
      toast.success("Query updated");
    }
    setEditingId(null);
    setEditText("");
  };

  const handleDelete = (id: string) => {
    removeSavedQuery(id);
    toast.success("Query removed");
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1200px] mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shadow-lg">
              <Bookmark className="w-5 h-5 text-white" />
            </div>
            Saved Queries
          </h1>
          <p className="text-muted-foreground mt-2 text-sm">
            Manage your bookmarked database queries.
          </p>
        </div>

        {/* Search */}
        <div className="relative max-w-md mb-6">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search saved queries..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-card border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/30 text-sm transition-all"
            aria-label="Search saved queries"
          />
        </div>

        {/* Grid */}
        {filteredQueries.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-20 bg-card border border-border rounded-2xl"
          >
            <Bookmark className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {searchQuery ? "No matching queries" : "No saved queries yet"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              {searchQuery
                ? "Try adjusting your search"
                : "Save queries from the AI Search page to access them quickly."}
            </p>
            {!searchQuery && (
              <button
                onClick={() => navigate("/search")}
                className="mt-6 px-5 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 transition-colors"
              >
                Go to AI Search
              </button>
            )}
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <AnimatePresence>
              {filteredQueries.map((q, idx) => (
                <motion.div
                  key={q.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: idx * 0.03 }}
                  whileHover={{ y: -2 }}
                  className="bg-card border border-border rounded-2xl p-5 hover:shadow-md hover:border-primary/10 transition-all duration-300"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <button
                      onClick={() => toggleFavoriteQuery(q.id)}
                      className="shrink-0 mt-0.5"
                      aria-label={q.isFavorite ? "Remove from favorites" : "Add to favorites"}
                    >
                      <Star
                        className={`w-5 h-5 transition-colors ${
                          q.isFavorite
                            ? "text-amber-500 fill-amber-500"
                            : "text-muted-foreground hover:text-amber-500"
                        }`}
                      />
                    </button>
                    <div className="flex items-center gap-1">
                      {editingId !== q.id && (
                        <button
                          onClick={() => handleEdit(q.id, q.query)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                          aria-label="Edit query"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(q.id)}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/5 transition-colors"
                        aria-label="Delete query"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {editingId === q.id ? (
                    <div className="mb-3">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        className="w-full p-3 bg-muted/30 border border-border rounded-xl text-sm text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-primary/30"
                        rows={2}
                        autoFocus
                      />
                      <div className="flex justify-end gap-2 mt-2">
                        <button
                          onClick={() => setEditingId(null)}
                          className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted/50"
                        >
                          <X className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleSaveEdit(q.id)}
                          className="p-1.5 rounded-lg text-primary hover:bg-primary/10"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm font-medium text-foreground mb-3 line-clamp-3">
                      {q.query}
                    </p>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {formatDate(q.createdAt)}
                    </span>
                    <button
                      onClick={() =>
                        navigate(`/search?q=${encodeURIComponent(q.query)}`)
                      }
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary text-xs font-medium rounded-lg hover:bg-primary/20 transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Run
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </motion.div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { api } from "../services/api";
import PostCard from "../components/PostCard";

export default function FeedPage() {
  const [posts, setPosts] = useState(null);
  const [sort, setSort] = useState("recent");
  const [composerText, setComposerText] = useState("");
  const [composerFile, setComposerFile] = useState(null);
  const [posting, setPosting] = useState(false);

  const load = async (sortMode = sort) => {
    const result = await api.getFeed({ sort: sortMode, page: 1, page_size: 20 });
    setPosts(result.posts);
  };

  useEffect(() => {
    load(sort);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort]);

  const submitPost = async (e) => {
    e.preventDefault();
    if (!composerText.trim() && !composerFile) return;
    setPosting(true);
    try {
      let media_path = null;
      if (composerFile) {
        const uploaded = await api.uploadFile(composerFile, "POST_MEDIA");
        media_path = uploaded.storage_path;
      }
      await api.createPost({ content: composerText.trim(), media_path });
      setComposerText("");
      setComposerFile(null);
      await load();
    } finally {
      setPosting(false);
    }
  };

  const handleDeleted = (postId) => setPosts((prev) => prev.filter((p) => p.post_id !== postId));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Community</h1>
          <p className="page-subtitle">See what other people are practicing this week.</p>
        </div>
      </div>

      <div className="feed-column">
        <form className="entry-card" onSubmit={submitPost} style={{ marginBottom: "var(--space-5)" }}>
          <textarea
            rows={2}
            placeholder="Share a milestone, a win, or what you practiced today…"
            value={composerText}
            onChange={(e) => setComposerText(e.target.value)}
            style={{
              width: "100%",
              border: "1px solid var(--paper-700)",
              borderRadius: 8,
              padding: "10px 12px",
              fontSize: 14.5,
              marginBottom: 10,
            }}
            maxLength={500}
          />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <input type="file" accept="image/*" onChange={(e) => setComposerFile(e.target.files?.[0] || null)} />
            <button className="btn btn-primary btn-sm" type="submit" disabled={posting}>
              {posting ? "Sharing…" : "Share"}
            </button>
          </div>
        </form>

        <div className="feed-filters">
          <button className={`filter-chip ${sort === "recent" ? "active" : ""}`} onClick={() => setSort("recent")}>
            Recent
          </button>
          <button className={`filter-chip ${sort === "top" ? "active" : ""}`} onClick={() => setSort("top")}>
            Most liked
          </button>
        </div>

        {posts === null ? (
          <p style={{ color: "var(--ink-600)" }}>Loading feed…</p>
        ) : posts.length === 0 ? (
          <div className="empty-state">
            <h3>The feed is quiet</h3>
            <p>Be the first to share what you've been practicing.</p>
          </div>
        ) : (
          posts.map((post) => <PostCard key={post.post_id} post={post} onDeleted={handleDeleted} />)
        )}
      </div>
    </div>
  );
}

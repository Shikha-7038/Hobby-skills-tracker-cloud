import { useState } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

function timeAgo(iso) {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  const units = [
    ["year", 31536000],
    ["month", 2592000],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [label, secs] of units) {
    const value = Math.floor(seconds / secs);
    if (value >= 1) return `${value} ${label}${value > 1 ? "s" : ""} ago`;
  }
  return "just now";
}

export default function PostCard({ post, onDeleted }) {
  const { user } = useAuth();
  const [liked, setLiked] = useState(post.liked_by_me);
  const [likeCount, setLikeCount] = useState(post.like_count);
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState(null);
  const [commentText, setCommentText] = useState("");
  const [busy, setBusy] = useState(false);

  const toggleLike = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (liked) {
        const updated = await api.unlikePost(post.post_id);
        setLiked(false);
        setLikeCount(updated.like_count);
      } else {
        const updated = await api.likePost(post.post_id);
        setLiked(true);
        setLikeCount(updated.like_count);
      }
    } catch {
      // silently ignore - a stale duplicate click is not worth surfacing
    } finally {
      setBusy(false);
    }
  };

  const loadComments = async () => {
    setShowComments((s) => !s);
    if (!comments) {
      const rows = await api.getComments(post.post_id);
      setComments(rows);
    }
  };

  const submitComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    const created = await api.addComment(post.post_id, commentText.trim());
    setComments((prev) => [...(prev || []), { ...created, author_name: user.name, author_username: user.username }]);
    setCommentText("");
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this post? This cannot be undone.")) return;
    await api.deletePost(post.post_id);
    onDeleted?.(post.post_id);
  };

  const isOwner = user?.user_id === post.author.user_id;

  return (
    <article className="post-card">
      <div className="post-header">
        <div className="avatar">
          {post.author.profile_picture ? (
            <img src={post.author.profile_picture} alt="" />
          ) : (
            post.author.name.charAt(0).toUpperCase()
          )}
        </div>
        <div>
          <div className="post-author-name">{post.author.name}</div>
          <div className="post-time">
            @{post.author.username} · {timeAgo(post.created_at)}
          </div>
        </div>
        {isOwner && (
          <button className="btn btn-danger btn-sm" style={{ marginLeft: "auto" }} onClick={handleDelete}>
            Delete
          </button>
        )}
      </div>

      {post.content && <p className="post-content">{post.content}</p>}
      {post.media_url && <img className="post-media" src={post.media_url} alt="" />}

      <div className="post-actions">
        <button className={`post-action-btn ${liked ? "liked" : ""}`} onClick={toggleLike}>
          {liked ? "♥" : "♡"} {likeCount}
        </button>
        <button className="post-action-btn" onClick={loadComments}>
          ◔ {post.comment_count} comment{post.comment_count === 1 ? "" : "s"}
        </button>
      </div>

      {showComments && (
        <div>
          <div className="comment-list">
            {(comments || []).map((c) => (
              <div className="comment-row" key={c.comment_id}>
                <span className="comment-author">{c.author_name}</span>
                {c.text}
              </div>
            ))}
            {comments && comments.length === 0 && (
              <div className="comment-row" style={{ color: "var(--ink-600)" }}>
                No comments yet. Be the first to cheer them on.
              </div>
            )}
          </div>
          <form className="comment-form" onSubmit={submitComment}>
            <input
              placeholder="Write a comment…"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              maxLength={500}
            />
            <button type="submit" className="btn btn-primary btn-sm">
              Post
            </button>
          </form>
        </div>
      )}
    </article>
  );
}

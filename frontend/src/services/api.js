const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function toUrl(path) {
  return `${API_BASE_URL}${path}`;
}

const TOKEN_KEY = "hobbytracker.session";

export function getSession() {
  const raw = localStorage.getItem(TOKEN_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function setSession(session) {
  if (session) {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

class ApiError extends Error {
  constructor(status, payload) {
    const message =
      (payload && (payload.message || payload.detail?.message || payload.detail)) ||
      "Something went wrong. Please try again.";
    super(typeof message === "string" ? message : "Something went wrong. Please try again.");
    this.status = status;
    this.field = payload?.field || payload?.detail?.field || null;
  }
}

let refreshPromise = null;

async function refreshAccessToken() {
  const session = getSession();
  if (!session?.refresh_token) throw new ApiError(401, { message: "Session expired" });
  const resp = await fetch(toUrl("/api/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });
  if (!resp.ok) {
    setSession(null);
    throw new ApiError(401, { message: "Session expired. Please log in again." });
  }
  const fresh = await resp.json();
  setSession({ ...session, ...fresh });
  return fresh;
}

/**
 * @param {string} path       e.g. "/api/skills"
 * @param {object} [options]
 * @param {string} [options.method]
 * @param {object} [options.json]        JSON body
 * @param {FormData} [options.form]      multipart body (file uploads)
 * @param {boolean} [options.auth]       attach the bearer token (default true)
 */
export async function apiRequest(path, options = {}) {
  const { method = "GET", json, form, auth = true } = options;
  const headers = {};
  let body;

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form !== undefined) {
    body = form; // browser sets multipart boundary automatically
  }

  const attach = () => {
    const session = getSession();
    if (auth && session?.access_token) {
      headers["Authorization"] = `Bearer ${session.access_token}`;
    }
  };
  attach();

  const url = toUrl(path);
  let response = await fetch(url, { method, headers, body });

  if (response.status === 401 && auth && getSession()?.refresh_token) {
    try {
      if (!refreshPromise) refreshPromise = refreshAccessToken().finally(() => (refreshPromise = null));
      await refreshPromise;
      attach();
      response = await fetch(url, { method, headers, body });
    } catch {
      // fall through - the caller will see the original 401
    }
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    throw new ApiError(response.status, payload);
  }
  return payload;
}

export const api = {
  register: (body) => apiRequest("/api/register", { method: "POST", json: body, auth: false }),
  login: (body) => apiRequest("/api/login", { method: "POST", json: body, auth: false }),
  logout: () => apiRequest("/api/logout", { method: "POST" }),

  getProfile: () => apiRequest("/api/profile"),
  updateProfile: (body) => apiRequest("/api/profile", { method: "PUT", json: body }),
  getPublicProfile: (username) => apiRequest(`/api/users/${username}`, { auth: false }),
  deleteAccount: () => apiRequest("/api/account", { method: "DELETE" }),

  getSkills: (status) => apiRequest(`/api/skills${status ? `?status=${status}` : ""}`),
  getSkill: (id) => apiRequest(`/api/skills/${id}`),
  createSkill: (body) => apiRequest("/api/skills", { method: "POST", json: body }),
  updateSkill: (id, body) => apiRequest(`/api/skills/${id}`, { method: "PUT", json: body }),
  deleteSkill: (id) => apiRequest(`/api/skills/${id}`, { method: "DELETE" }),

  getGoals: (skillId) => apiRequest(`/api/goals${skillId ? `?skill_id=${skillId}` : ""}`),
  createGoal: (body) => apiRequest("/api/goals", { method: "POST", json: body }),
  updateGoal: (id, body) => apiRequest(`/api/goals/${id}`, { method: "PUT", json: body }),

  logPractice: (body) => apiRequest("/api/practice", { method: "POST", json: body }),
  getSkillPractice: (skillId) => apiRequest(`/api/skills/${skillId}/practice`),

  createPost: (body) => apiRequest("/api/posts", { method: "POST", json: body }),
  getFeed: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/api/feed${qs ? `?${qs}` : ""}`, { auth: !!getSession() });
  },
  deletePost: (id) => apiRequest(`/api/posts/${id}`, { method: "DELETE" }),
  reportPost: (id, reason) => apiRequest(`/api/posts/${id}/report`, { method: "POST", json: { reason } }),

  likePost: (id) => apiRequest(`/api/posts/${id}/like`, { method: "POST" }),
  unlikePost: (id) => apiRequest(`/api/posts/${id}/like`, { method: "DELETE" }),
  getComments: (id) => apiRequest(`/api/posts/${id}/comments`, { auth: false }),
  addComment: (id, text) => apiRequest(`/api/posts/${id}/comments`, { method: "POST", json: { text } }),
  deleteComment: (id) => apiRequest(`/api/comments/${id}`, { method: "DELETE" }),

  followUser: (id) => apiRequest(`/api/users/${id}/follow`, { method: "POST" }),
  unfollowUser: (id) => apiRequest(`/api/users/${id}/follow`, { method: "DELETE" }),

  uploadFile: (file, kind, skillId) => {
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    if (skillId) form.append("skill_id", skillId);
    return apiRequest("/api/files/upload", { method: "POST", form });
  },

  getDashboard: () => apiRequest("/api/analytics/dashboard"),
  search: (q) => apiRequest(`/api/search?q=${encodeURIComponent(q)}`, { auth: false }),
  getTrending: () => apiRequest("/api/community/trending", { auth: false }),
};

export { ApiError };
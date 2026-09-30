/**
 * utils/router.js
 * ================
 * A deliberately tiny hash-based router. The app only has a handful of
 * screens, so pulling in react-router-dom would be one more dependency for
 * a student to install for very little benefit - this hook is ~30 lines
 * and covers navigate(), the current path, and simple ":param" segments.
 *
 * URLs look like:  #/skills/skl_ab12cd34/practice
 */
import { useCallback, useEffect, useState } from "react";

function currentHash() {
  return window.location.hash.replace(/^#/, "") || "/";
}

export function useHashRoute() {
  const [path, setPath] = useState(currentHash());

  useEffect(() => {
    const onChange = () => setPath(currentHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = useCallback((to) => {
    window.location.hash = to;
  }, []);

  return [path, navigate];
}

/** Matches "/skills/:id/practice" against "/skills/skl_123/practice" -> {id: "skl_123"} | null */
export function matchRoute(pattern, path) {
  const patternParts = pattern.split("/").filter(Boolean);
  const pathParts = path.split("/").filter(Boolean);
  if (patternParts.length !== pathParts.length) return null;
  const params = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(":")) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i]);
    } else if (patternParts[i] !== pathParts[i]) {
      return null;
    }
  }
  return params;
}

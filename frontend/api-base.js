/**
 * JYOTISH API Base URL Resolver
 * ================================
 * Determines where to send API requests based on the current environment:
 *
 *  1. LOCAL DEV (file:// or localhost)  → http://localhost:8080
 *  2. GITHUB PAGES (production)         → reads JYOTISH_API_BASE from localStorage
 *                                          (default: http://localhost:8080)
 *                                          User must set this if backend runs elsewhere.
 *
 * Override priority (highest → lowest):
 *   window.__JYOTISH_API_BASE__  →  localStorage["JYOTISH_API_BASE"]  →  meta tag  →  auto-detect
 *
 * How to set from browser console (for GitHub Pages users):
 *   localStorage.setItem("JYOTISH_API_BASE", "http://YOUR_LAPTOP_IP:8080");
 *   location.reload();
 */
(function () {
  const LOCAL_API_PORT = "8080";
  // Default backend URL when running on GitHub Pages
  // Change this to your Ngrok / Cloudflare Tunnel URL if you expose publicly
  const GITHUB_PAGES_DEFAULT_BACKEND = "http://localhost:" + LOCAL_API_PORT;

  function storageValue(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function cleanBase(value) {
    return String(value || "").replace(/\/+$/, "");
  }

  function isGitHubPages() {
    const host = window.location.hostname;
    return host.endsWith(".github.io") || host.endsWith(".github.com");
  }

  function resolveJyotishApiBase() {
    // 1. Explicit programmatic override (highest priority)
    if (window.__JYOTISH_API_BASE__) {
      return cleanBase(window.__JYOTISH_API_BASE__);
    }

    // 2. Saved user preference in localStorage
    const stored = storageValue("JYOTISH_API_BASE");
    if (stored) return cleanBase(stored);

    // 3. Meta tag override
    const meta = document.querySelector('meta[name="jyotish-api-base"]');
    if (meta && meta.content) return cleanBase(meta.content);

    // 4. file:// protocol (opening HTML directly)
    if (window.location.protocol === "file:") {
      return "http://localhost:" + LOCAL_API_PORT;
    }

    // 5. GitHub Pages — use the stored preference or default to localhost
    if (isGitHubPages()) {
      return GITHUB_PAGES_DEFAULT_BACKEND;
    }

    // 6. Running on localhost but different port (e.g., frontend on 3000)
    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    if (isLocal && window.location.port !== LOCAL_API_PORT) {
      return "http://" + host + ":" + LOCAL_API_PORT;
    }

    // 7. Same origin (backend serves frontend directly)
    return cleanBase(window.location.origin);
  }

  function resolveJyotishVideoBase() {
    if (window.__JYOTISH_VIDEO_BASE__) {
      return cleanBase(window.__JYOTISH_VIDEO_BASE__);
    }

    const stored = storageValue("JYOTISH_VIDEO_SIGNALING_URL");
    if (stored) return cleanBase(stored);

    const meta = document.querySelector('meta[name="jyotish-video-base"]');
    if (meta && meta.content) return cleanBase(meta.content);

    if (window.location.protocol === "file:") {
      return "http://localhost:5000";
    }

    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    if (isLocal) {
      return "http://" + host + ":5000";
    }

    if (host.endsWith(".onrender.com")) {
      return "https://jyotish-video-signaling.onrender.com";
    }

    return cleanBase(window.location.origin);
  }

  function jyotishPageUrl(path) {
    const cleanPath = String(path || "").replace(/^\/+/, "");
    return window.location.protocol === "file:" ? cleanPath : "/" + cleanPath;
  }

  window.resolveJyotishApiBase = resolveJyotishApiBase;
  window.resolveJyotishVideoBase = resolveJyotishVideoBase;
  window.jyotishPageUrl = jyotishPageUrl;
  window.JYOTISH_API_BASE = resolveJyotishApiBase();
  window.JYOTISH_VIDEO_BASE = resolveJyotishVideoBase();

  // Expose a helper to change the backend URL at runtime (useful for GitHub Pages)
  window.setJyotishBackend = function (url) {
    try {
      localStorage.setItem("JYOTISH_API_BASE", url.replace(/\/+$/, ""));
      window.JYOTISH_API_BASE = url.replace(/\/+$/, "");
      console.log("[Jyotish] Backend URL set to:", window.JYOTISH_API_BASE);
    } catch (e) {
      console.error("[Jyotish] Could not save backend URL:", e);
    }
  };

  window.setJyotishVideoBackend = function (url) {
    try {
      localStorage.setItem("JYOTISH_VIDEO_SIGNALING_URL", url.replace(/\/+$/, ""));
      window.JYOTISH_VIDEO_BASE = url.replace(/\/+$/, "");
      console.log("[Jyotish] Video signaling URL set to:", window.JYOTISH_VIDEO_BASE);
    } catch (e) {
      console.error("[Jyotish] Could not save video URL:", e);
    }
  };
})();

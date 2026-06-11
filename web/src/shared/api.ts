/** Dual-mode data client.
 *
 * LIVE mode  — a local FastAPI bridge (http://localhost:8000) serves real
 *              data from the owner's machine: agentmemory, wiki, research
 *              boards, skills, git projects.
 * DEMO mode  — static sanitized snapshots under /demo/*.json so the public
 *              Vercel deployment is rich without exposing private data.
 */

const LOCAL_BASE = "http://127.0.0.1:8000";

export type Mode = "live" | "demo";

let mode: Mode = "demo";
let detected = false;

export function currentMode(): Mode {
  return mode;
}

export async function detectMode(): Promise<Mode> {
  if (detected) return mode;
  // Public deployments can never reach a loopback bridge (the browser blocks
  // private-network requests from https origins) — skip the probe entirely.
  const host = window.location.hostname;
  if (host !== "localhost" && host !== "127.0.0.1") {
    mode = "demo";
    detected = true;
    return mode;
  }
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 1500);
    const r = await fetch(`${LOCAL_BASE}/api/health`, { signal: ctrl.signal });
    clearTimeout(t);
    mode = r.ok ? "live" : "demo";
  } catch {
    mode = "demo";
  }
  detected = true;
  return mode;
}

async function fetchJson<T>(url: string, timeoutMs = 8000): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { signal: ctrl.signal });
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return (await r.json()) as T;
  } finally {
    clearTimeout(t);
  }
}

/** Fetch from the live bridge with a demo-snapshot fallback. */
export async function getData<T>(liveEndpoint: string, demoFile: string): Promise<T> {
  if (mode === "live") {
    try {
      return await fetchJson<T>(`${LOCAL_BASE}${liveEndpoint}`);
    } catch {
      // graceful degradation: live bridge hiccup -> demo snapshot
    }
  }
  return fetchJson<T>(`/demo/${demoFile}`);
}

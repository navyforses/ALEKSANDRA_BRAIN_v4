import { readFileSync } from "node:fs";
import { resolve } from "node:path";

type Query = Record<string, string | number | boolean | null | undefined>;

export type CountResult = {
  configured: boolean;
  count: number;
  error?: string;
};

export type RowsResult<T> = {
  configured: boolean;
  rows: T[];
  error?: string;
};

const missingConfig = {
  configured: false,
  error: "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not configured",
};

let rootEnvLoaded = false;

function loadRootEnvForLocalDev() {
  if (rootEnvLoaded) {
    return;
  }
  rootEnvLoaded = true;

  try {
    const envPath = resolve(process.cwd(), "..", ".env");
    const contents = readFileSync(envPath, "utf8");
    for (const line of contents.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
        continue;
      }
      const [rawKey, ...rest] = trimmed.split("=");
      const key = rawKey.trim();
      const value = rest.join("=").trim().replace(/^['"]|['"]$/g, "");
      if (key && process.env[key] === undefined) {
        process.env[key] = value;
      }
    }
  } catch {
    // Vercel and other hosted runtimes should use real environment variables.
  }
}

function getConfig() {
  loadRootEnvForLocalDev();
  const url = process.env.SUPABASE_URL?.replace(/\/$/, "");
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return null;
  }
  return { url, key };
}

function buildUrl(path: string, query: Query = {}) {
  const config = getConfig();
  if (!config) {
    return null;
  }

  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.set(key, String(value));
    }
  });

  const suffix = params.toString();
  return {
    href: `${config.url}/rest/v1/${path}${suffix ? `?${suffix}` : ""}`,
    key: config.key,
  };
}

export async function getRows<T>(
  path: string,
  query: Query = {},
): Promise<RowsResult<T>> {
  const request = buildUrl(path, query);
  if (!request) {
    return { ...missingConfig, rows: [] };
  }

  try {
    // Remote Supabase REST is server-only and PHI-free; MRI/NIfTI data never uses this path.
    const response = await fetch(request.href, { /* allow-remote */
      cache: "no-store",
      headers: {
        apikey: request.key,
        Authorization: `Bearer ${request.key}`,
        Prefer: "count=none",
      },
    });
    if (!response.ok) {
      return {
        configured: true,
        rows: [],
        error: `Supabase ${path} returned HTTP ${response.status}`,
      };
    }
    return { configured: true, rows: (await response.json()) as T[] };
  } catch (error) {
    return {
      configured: true,
      rows: [],
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function getCount(
  path: string,
  query: Query = {},
): Promise<CountResult> {
  const request = buildUrl(path, { ...query, select: query.select ?? "id" });
  if (!request) {
    return { ...missingConfig, count: 0 };
  }

  try {
    // Remote Supabase REST is server-only and PHI-free; MRI/NIfTI data never uses this path.
    const response = await fetch(request.href, { /* allow-remote */
      cache: "no-store",
      headers: {
        apikey: request.key,
        Authorization: `Bearer ${request.key}`,
        Prefer: "count=exact",
        Range: "0-0",
      },
    });
    const range = response.headers.get("content-range");
    if (range?.includes("/")) {
      const total = Number(range.split("/").at(-1));
      return { configured: true, count: Number.isFinite(total) ? total : 0 };
    }
    if (!response.ok) {
      return {
        configured: true,
        count: 0,
        error: `Supabase ${path} returned HTTP ${response.status}`,
      };
    }
    const rows = (await response.json()) as unknown[];
    return { configured: true, count: rows.length };
  } catch (error) {
    return {
      configured: true,
      count: 0,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function updateHypothesisReview(
  id: string,
  status: "confirmed" | "under_review" | "rejected",
  outcome: string,
) {
  const request = buildUrl("hypotheses", { id: `eq.${id}` });
  if (!request) {
    return missingConfig;
  }

  try {
    // Remote Supabase REST is server-only and PHI-free; MRI/NIfTI data never uses this path.
    const response = await fetch(request.href, { /* allow-remote */
      method: "PATCH",
      cache: "no-store",
      headers: {
        apikey: request.key,
        Authorization: `Bearer ${request.key}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify({
        status,
        outcome,
        reviewed_at: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      return {
        configured: true,
        error: `Supabase hypotheses PATCH returned HTTP ${response.status}`,
      };
    }
    return { configured: true };
  } catch (error) {
    return {
      configured: true,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

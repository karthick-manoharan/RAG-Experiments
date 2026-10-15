/** Shared build/browser validation. Never include the configured value in errors. */
export function resolveApiBaseUrl(value: string | undefined, production: boolean): string {
  if (value === undefined && !production) return "http://localhost:8000";
  const message = "Set NEXT_PUBLIC_API_BASE_URL to a valid HTTPS backend URL (no loopback, credentials, query or fragment) before building production.";
  try {
    if (!value || value !== value.trim() || /\s|\\/.test(value)) throw new Error();
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/\.$/, "");
    const loopback = host === "localhost" || host.endsWith(".localhost") ||
      host.startsWith("127.") || host === "[::1]" || host === "0.0.0.0" ||
      host.startsWith("[::ffff:7f");
    if (!/^https?:\/\//.test(value) || url.username || url.password || url.search || url.hash ||
      (production && (url.protocol !== "https:" || loopback))) throw new Error();
    return url.toString().replace(/\/+$/, "");
  } catch {
    throw new Error(message);
  }
}

import { authorizedFetch, saveBlob } from "@/lib/api/client";

export type ReportFormat = "json" | "csv" | "pdf";

/** Authenticated file download: report endpoints require a Bearer token,
 * so a plain <a href> can't be used. Fetches the real report (refreshing an
 * expired access token if needed) and saves it. Throws on failure so the
 * caller can show a real error instead of a silent no-op.
 */
export async function downloadReport(
  kind: "scan" | "case",
  id: string,
  format: ReportFormat,
): Promise<void> {
  const path = kind === "scan" ? `/messages/${id}/report` : `/cases/${id}/report`;
  const response = await authorizedFetch(`${path}?format=${format}`);
  saveBlob(await response.blob(), `scamguard-${kind}-${id}.${format}`);
}

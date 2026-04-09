import type { Asset, Scan } from "@/types/api"

export function hasBrowserInputs(assets: Asset[]) {
  return assets.some((asset) => asset.entity_type === "device" || asset.entity_type === "url")
}

export function hasCompletedBrowserReview(assets: Asset[], scans: Scan[]) {
  const browserAssets = assets.filter(
    (asset) => asset.entity_type === "device" || asset.entity_type === "url",
  )

  if (browserAssets.length === 0) return false

  const latestBrowserInputAt = Math.max(
    ...browserAssets.map((asset) => Date.parse(asset.updated_at || asset.created_at)),
  )

  return scans.some((scan) => {
    if (scan.status !== "completed" || !scan.completed_at) return false
    const completedAt = Date.parse(scan.completed_at)
    return Number.isFinite(completedAt) && completedAt >= latestBrowserInputAt
  })
}

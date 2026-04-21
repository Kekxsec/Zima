"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { monogramColor } from "./SourceBadge"

interface ServiceLogoProps {
  serviceName: string
  domain: string | null
  size?: "sm" | "md" | "lg"
  className?: string
}

const SIZE_CLASSES = {
  sm: "h-8 w-8 rounded-lg text-xs",
  md: "h-10 w-10 rounded-xl text-sm",
  lg: "h-12 w-12 rounded-xl text-lg",
}

export function ServiceLogo({ serviceName, domain, size = "md", className }: ServiceLogoProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const initial = (serviceName[0] ?? "?").toUpperCase()
  const color = monogramColor(serviceName)
  const sizeClass = SIZE_CLASSES[size]
  const faviconUrl = domain
    ? `https://icons.duckduckgo.com/ip3/${domain}.ico`
    : null

  if (faviconUrl && !imgFailed) {
    return (
      <div className={cn("shrink-0 flex items-center justify-center overflow-hidden bg-white/5", sizeClass, className)}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={faviconUrl}
          alt=""
          className="h-full w-full object-contain p-1.5"
          onError={() => setImgFailed(true)}
        />
      </div>
    )
  }

  return (
    <div
      className={cn(
        "shrink-0 flex items-center justify-center font-bold",
        sizeClass,
        color,
        className,
      )}
    >
      {initial}
    </div>
  )
}

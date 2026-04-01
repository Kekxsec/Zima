"use client"

import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

interface Step {
  label: string
}

interface OnboardingStepperProps {
  steps: Step[]
  currentStep: number
}

export function OnboardingStepper({ steps, currentStep }: OnboardingStepperProps) {
  return (
    <div className="flex items-center gap-0">
      {steps.map((step, i) => {
        const isDone = i < currentStep
        const isActive = i === currentStep
        return (
          <div key={i} className="flex items-center">
            {/* Circle */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full border-2 text-xs font-semibold transition-colors",
                  isDone && "bg-primary border-primary text-white",
                  isActive && "bg-transparent border-primary text-primary",
                  !isDone && !isActive && "bg-transparent border-slate-600 text-slate-500",
                )}
              >
                {isDone ? <Check className="w-4 h-4" /> : <span>{i + 1}</span>}
              </div>
              <span
                className={cn(
                  "mt-1.5 text-[10px] font-medium whitespace-nowrap",
                  isActive ? "text-slate-200" : isDone ? "text-slate-400" : "text-slate-600",
                )}
              >
                {step.label}
              </span>
            </div>
            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "w-12 h-0.5 mx-1 mb-5 transition-colors",
                  i < currentStep ? "bg-primary" : "bg-slate-700",
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

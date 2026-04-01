"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { Plus, X, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper"
import { useOnboardingStore } from "@/lib/store/onboarding"

const COUNTRY_CODES = [
  { code: "+1",   label: "+1  US/CA" },
  { code: "+44",  label: "+44  UK" },
  { code: "+33",  label: "+33  FR" },
  { code: "+49",  label: "+49  DE" },
  { code: "+34",  label: "+34  ES" },
  { code: "+39",  label: "+39  IT" },
  { code: "+31",  label: "+31  NL" },
  { code: "+32",  label: "+32  BE" },
  { code: "+41",  label: "+41  CH" },
  { code: "+43",  label: "+43  AT" },
  { code: "+46",  label: "+46  SE" },
  { code: "+47",  label: "+47  NO" },
  { code: "+45",  label: "+45  DK" },
  { code: "+358", label: "+358 FI" },
  { code: "+48",  label: "+48  PL" },
  { code: "+61",  label: "+61  AU" },
  { code: "+64",  label: "+64  NZ" },
  { code: "+81",  label: "+81  JP" },
  { code: "+82",  label: "+82  KR" },
  { code: "+86",  label: "+86  CN" },
  { code: "+91",  label: "+91  IN" },
  { code: "+55",  label: "+55  BR" },
  { code: "+52",  label: "+52  MX" },
  { code: "+27",  label: "+27  ZA" },
  { code: "+971", label: "+971 AE" },
  { code: "+65",  label: "+65  SG" },
]

const STEPS = [
  { label: "Welcome" },
  { label: "Your Identity" },
  { label: "First Scan" },
  { label: "Results" },
]

const schema = z.object({
  firstName: z.string().min(1, "Required"),
  lastName: z.string().min(1, "Required"),
  phone: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

export default function IdentityPage() {
  const router = useRouter()
  const setIdentity = useOnboardingStore((s) => s.setIdentity)
  const setPendingEmailVerifications = useOnboardingStore((s) => s.setPendingEmailVerifications)
  const setPendingPhoneVerifications = useOnboardingStore((s) => s.setPendingPhoneVerifications)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const [dialCode, setDialCode] = useState("+44")

  type Tagged = { id: string; value: string }
  const mkEntry = (): Tagged => ({ id: crypto.randomUUID(), value: "" })

  const [usernames, setUsernames] = useState<Tagged[]>([mkEntry()])
  const [emailDomains, setEmailDomains] = useState<Tagged[]>([mkEntry()])

  function addUsername() {
    setUsernames((prev) => [...prev, mkEntry()])
  }
  function removeUsername(id: string) {
    setUsernames((prev) => prev.filter((u) => u.id !== id))
  }
  function updateUsername(id: string, value: string) {
    setUsernames((prev) => prev.map((u) => (u.id === id ? { ...u, value } : u)))
  }

  function addDomain() {
    setEmailDomains((prev) => [...prev, mkEntry()])
  }
  function removeDomain(id: string) {
    setEmailDomains((prev) => prev.filter((d) => d.id !== id))
  }
  function updateDomain(id: string, value: string) {
    setEmailDomains((prev) => prev.map((d) => (d.id === id ? { ...d, value } : d)))
  }

  function onSubmit(values: FormValues) {
    const cleanedUsernames = usernames.map((u) => u.value).filter((v) => v.trim() !== "")
    const cleanedDomains = emailDomains
      .map((d) => d.value.trim().toLowerCase())
      .filter((v) => v !== "" && v.includes("@"))
    const rawPhone = values.phone?.trim() ?? ""
    // Strip spaces and leading zeros, then prepend dial code
    const localNumber = rawPhone.replace(/\s/g, "").replace(/^0+/, "")
    const cleanedPhone = rawPhone !== "" ? `${dialCode}${localNumber}` : ""

    setIdentity({
      firstName: values.firstName,
      lastName: values.lastName,
      phone: cleanedPhone,
      usernames: cleanedUsernames,
      emailDomains: cleanedDomains,
    })

    const needsVerify = cleanedDomains.length > 0 || cleanedPhone !== ""
    if (cleanedDomains.length > 0) setPendingEmailVerifications(cleanedDomains)
    if (cleanedPhone !== "") setPendingPhoneVerifications([cleanedPhone])

    if (needsVerify) {
      router.push("/onboarding/verify")
    } else {
      router.push("/onboarding/scan")
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center px-4 py-12">
      {/* Stepper */}
      <div className="mb-10">
        <OnboardingStepper steps={STEPS} currentStep={1} />
      </div>

      <div className="w-full max-w-2xl">
        <h1 className="text-2xl font-bold text-white mb-2">Tell us about your identity</h1>
        <p className="text-slate-400 text-sm mb-8">
          This helps us build a complete picture of your digital footprint. All fields except name are optional.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* ── Row 1: Name ─────────────────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="firstName" className="text-slate-300">First name</Label>
              <Input
                id="firstName"
                placeholder="Alice"
                {...register("firstName")}
                className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-primary"
              />
              {errors.firstName && (
                <p className="text-xs text-red-400">{errors.firstName.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="lastName" className="text-slate-300">Last name</Label>
              <Input
                id="lastName"
                placeholder="Smith"
                {...register("lastName")}
                className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-primary"
              />
              {errors.lastName && (
                <p className="text-xs text-red-400">{errors.lastName.message}</p>
              )}
            </div>
          </div>

          {/* ── Row 2: Phone + Usernames ─────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Phone */}
            <div className="space-y-1.5">
              <Label htmlFor="phone" className="text-slate-300">
                Phone number <span className="text-slate-500 font-normal">(optional)</span>
              </Label>
              <div className="flex gap-2">
                <Select value={dialCode} onValueChange={setDialCode}>
                  <SelectTrigger className="w-[110px] shrink-0 bg-slate-800 border-slate-700 text-white focus:ring-primary">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700 text-white max-h-60">
                    {COUNTRY_CODES.map(({ code, label }) => (
                      <SelectItem
                        key={code}
                        value={code}
                        className="font-mono text-xs focus:bg-slate-700 focus:text-white"
                      >
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="7700 900000"
                  {...register("phone")}
                  className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-primary"
                />
              </div>
              <p className="text-xs text-slate-500">
                Used to check if your number appears in breaches.
              </p>
            </div>

            {/* Usernames */}
            <div className="space-y-2">
              <Label className="text-slate-300">
                Usernames <span className="text-slate-500 font-normal">(optional)</span>
              </Label>
              <div className="space-y-2">
                {usernames.map(({ id, value }) => (
                  <div key={id} className="flex gap-2">
                    <Input
                      value={value}
                      onChange={(e) => updateUsername(id, e.target.value)}
                      placeholder="e.g. alice_s"
                      className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-primary"
                    />
                    {usernames.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="text-slate-500 hover:text-red-400 hover:bg-slate-700 shrink-0"
                        onClick={() => removeUsername(id)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-slate-400 hover:text-slate-200 hover:bg-slate-700 px-2 h-8"
                  onClick={addUsername}
                >
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add username
                </Button>
              </div>
              <p className="text-xs text-slate-500">
                Online handles you commonly use.
              </p>
            </div>
          </div>

          {/* ── Row 3: Additional emails ─────────────────────────────── */}
          <div className="space-y-2">
            <Label className="text-slate-300">
              Additional email addresses <span className="text-slate-500 font-normal">(optional)</span>
            </Label>
            <p className="text-xs text-slate-500 mb-2">
              Other email addresses you own. Each will need OTP verification before scanning. Your sign-in email is already included.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {emailDomains.map(({ id, value }) => (
                <div key={id} className="flex gap-2">
                  <Input
                    value={value}
                    onChange={(e) => updateDomain(id, e.target.value)}
                    placeholder="you@other-domain.com"
                    className="bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-primary"
                  />
                  {emailDomains.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="text-slate-500 hover:text-red-400 hover:bg-slate-700 shrink-0"
                      onClick={() => removeDomain(id)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-slate-200 hover:bg-slate-700 px-2 h-8 mt-1"
              onClick={addDomain}
            >
              <Plus className="w-3.5 h-3.5 mr-1" /> Add email address
            </Button>
          </div>

          {/* ── Submit ───────────────────────────────────────────────── */}
          <div className="flex justify-end pt-2">
            <Button type="submit" size="lg" className="gap-2 px-8">
              Continue <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

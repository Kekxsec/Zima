import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Terms of Service — Zima",
  description: "Terms and conditions governing use of the Zima platform.",
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <div className="text-sm text-slate-400 leading-relaxed space-y-2">{children}</div>
    </section>
  )
}

export default function TermsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Terms of Service</h1>
        <p className="text-sm text-slate-500">Last updated: April 2026</p>
      </div>

      <p className="text-sm text-slate-400 leading-relaxed">
        These Terms of Service (&quot;Terms&quot;) govern your use of Zima, an identity protection
        platform operated by Zima (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;). By creating an
        account or using the service, you agree to these Terms.
      </p>

      <Section title="1. Eligibility">
        <p>
          You must be at least 18 years old and capable of forming a legally binding contract to use
          Zima. By using the service, you represent that you meet this requirement.
        </p>
      </Section>

      <Section title="2. Acceptable Use">
        <p>You agree to use Zima only for lawful purposes and only with respect to your own identity assets — email addresses, usernames, and phone numbers that you own or are authorised to monitor.</p>
        <p>You must not:</p>
        <ul className="list-disc list-inside space-y-1 pl-2">
          <li>Use Zima to monitor or collect information about other people without their explicit consent</li>
          <li>Attempt to reverse-engineer, scrape, or abuse the Zima API</li>
          <li>Submit false or misleading identity assets</li>
          <li>Use the service to facilitate harassment, stalking, or surveillance of others</li>
          <li>Attempt to circumvent authentication, rate limits, or security controls</li>
        </ul>
      </Section>

      <Section title="3. Account Security">
        <p>
          You are responsible for maintaining the security of your account. Zima uses OTP-only
          authentication — no passwords are stored. You agree to notify us immediately if you suspect
          unauthorised access to your account.
        </p>
      </Section>

      <Section title="4. Scan Results and Accuracy">
        <p>
          Zima aggregates data from third-party breach and OSINT sources. We make no guarantees about
          the completeness or accuracy of scan results. Results reflect what is discoverable through the
          data sources Zima queries at the time of scanning and may not be exhaustive.
        </p>
        <p>
          Zima is an informational tool. It does not constitute legal, security, or professional advice.
          You are responsible for the actions you take based on Zima&apos;s output.
        </p>
      </Section>

      <Section title="5. Subscriptions and Billing">
        <p>
          Zima offers free and paid subscription plans. Paid plans are billed through Stripe. By
          subscribing, you authorise recurring charges at the intervals displayed at the time of
          purchase. You may cancel at any time via account settings; cancellation takes effect at the
          end of your current billing period.
        </p>
        <p>
          We reserve the right to modify pricing with 30 days&apos; notice. If you disagree with a
          pricing change, you may cancel before the change takes effect.
        </p>
      </Section>

      <Section title="6. Intellectual Property">
        <p>
          Zima and its content, features, and functionality are owned by us and are protected by
          copyright, trademark, and other intellectual property laws. You are granted a limited,
          non-exclusive, non-transferable licence to use the service for its intended purpose.
        </p>
      </Section>

      <Section title="7. Data and Privacy">
        <p>
          Your use of Zima is also governed by our{" "}
          <a href="/privacy" className="text-violet-400 hover:text-violet-300 underline">
            Privacy Policy
          </a>
          , which is incorporated into these Terms by reference.
        </p>
      </Section>

      <Section title="8. Limitation of Liability">
        <p>
          To the maximum extent permitted by law, Zima shall not be liable for any indirect,
          incidental, special, consequential, or punitive damages arising from your use of the service,
          including but not limited to loss of data, loss of profits, or any harm resulting from
          reliance on scan results.
        </p>
        <p>
          Our total liability to you for any claim arising from use of the service shall not exceed the
          amount you paid us in the 12 months preceding the claim.
        </p>
      </Section>

      <Section title="9. Disclaimers">
        <p>
          The service is provided &quot;as is&quot; and &quot;as available&quot; without warranties of
          any kind, express or implied. We do not warrant that the service will be uninterrupted,
          error-free, or free from security vulnerabilities.
        </p>
      </Section>

      <Section title="10. Termination">
        <p>
          You may delete your account at any time from account settings. We may suspend or terminate
          your account if you violate these Terms or if we discontinue the service, with reasonable
          notice where practicable.
        </p>
      </Section>

      <Section title="11. Changes to These Terms">
        <p>
          We may update these Terms from time to time. Material changes will be communicated by email
          at least 14 days before they take effect. Continued use after the effective date constitutes
          acceptance.
        </p>
      </Section>

      <Section title="12. Governing Law">
        <p>
          These Terms are governed by the laws of England and Wales. Disputes shall be subject to the
          exclusive jurisdiction of the courts of England and Wales.
        </p>
      </Section>

      <Section title="13. Contact">
        <p>
          For questions about these Terms, contact us at{" "}
          <span className="text-violet-400">legal@zima.app</span>.
        </p>
      </Section>
    </div>
  )
}

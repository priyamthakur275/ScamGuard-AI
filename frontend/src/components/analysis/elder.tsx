"use client";

import { useState } from "react";
import { Phone } from "lucide-react";
import { useElderMode } from "@/components/analysis/protect-features";
import type { AnalysisResult } from "@/types";
import { cn } from "@/lib/utils";

type Lang = "en" | "hi";

const TXT = {
  en: {
    scam: "This is a scam.", warn: "Be careful. This may be a scam.", safe: "This looks genuine.",
    rules: ["Do not reply or call back.", "Never share an OTP, PIN or card number.", "Do not pay anyone.", "Talk to your family before you do anything."],
    safeNote: "Even so, never share your OTP with anyone.", call: "Call 1930 (free cyber helpline)",
    qTitle: "No message to paste? Answer these instead.",
    qSub: "Tick what happened on the call or message. Nothing is sent anywhere.",
    qs: [
      ["secret", "They asked for an OTP, PIN, password or card number"],
      ["pay", "They asked you to pay: a fee, fine, refund, prize or 'verification' amount"],
      ["threat", "They said police, CBI, court or arrest, or told you to keep it secret"],
      ["block", "They said your account, SIM, electricity or gas will be blocked or cut today"],
      ["app", "They sent a link or asked you to install an app or share your screen"],
    ] as [string, string][],
    check: "Check", clear: "Clear",
    none: "Nothing you ticked is a scam sign. If you are still unsure, call the company on the number printed on your card or bill.",
    family: "Copy a note for your family",
    copied: "Copied. Paste it in WhatsApp.",
  },
  hi: {
    scam: "यह धोखा है।", warn: "सावधान। यह धोखा हो सकता है।", safe: "यह असली लगता है।",
    rules: ["जवाब न दें, वापस कॉल न करें।", "OTP, PIN या कार्ड नंबर कभी न बताएँ।", "किसी को पैसे न भेजें।", "कुछ भी करने से पहले परिवार से बात करें।"],
    safeNote: "फिर भी, अपना OTP किसी को न बताएँ।", call: "1930 पर कॉल करें (मुफ़्त साइबर हेल्पलाइन)",
    qTitle: "मैसेज नहीं है? ये सवाल भरें।",
    qSub: "कॉल या मैसेज में जो हुआ उस पर टिक करें। कुछ भी कहीं नहीं भेजा जाता।",
    qs: [
      ["secret", "OTP, PIN, पासवर्ड या कार्ड नंबर माँगा"],
      ["pay", "पैसे माँगे: फ़ीस, जुर्माना, रिफ़ंड, इनाम या 'वेरिफ़िकेशन' राशि"],
      ["threat", "पुलिस, CBI, कोर्ट या गिरफ़्तारी की बात की, या किसी को न बताने को कहा"],
      ["block", "कहा कि आज खाता, SIM, बिजली या गैस बंद हो जाएगी"],
      ["app", "लिंक भेजा या कोई ऐप डालने या स्क्रीन शेयर करने को कहा"],
    ] as [string, string][],
    check: "जाँचें", clear: "साफ़ करें",
    none: "आपके टिक में धोखे का कोई संकेत नहीं है। फिर भी शक हो तो कार्ड या बिल पर छपे नंबर पर कंपनी को कॉल करें।",
    family: "परिवार के लिए नोट कॉपी करें",
    copied: "कॉपी हो गया। WhatsApp में पेस्ट करें।",
  },
};

// The questions map onto the scam intents of the risk engine's intent layer
// (asks_for_secret, pay_to_receive / move_money, legal_threat / secrecy,
// account_threat, link / remote_access_app). Any one of the first three is a
// scam in practice; the last two alone call for caution.
const STRONG = new Set(["secret", "pay", "threat"]);

function Card({ level, lang, note }: { level: "scam" | "warn" | "safe"; lang: Lang; note?: string }) {
  const T = TXT[lang] ?? TXT.en;
  const tone = { scam: "border-destructive text-destructive", warn: "border-caution text-caution", safe: "border-safe text-safe" }[level];
  return (
    <div role="status" className={cn("rounded-lg border-l-4 border-y border-r border-y-border border-r-border bg-card p-5", tone)}>
      <p className="text-xl font-semibold">{T[level]}</p>
      {level === "safe" ? (
        <p className="mt-2 text-base text-foreground">{note ?? T.safeNote}</p>
      ) : (
        <>
          <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-base text-foreground">
            {T.rules.map((r) => <li key={r}>{r}</li>)}
          </ol>
          <a href="tel:1930" className="mt-4 inline-flex items-center gap-2 rounded-md bg-destructive px-4 py-2.5 text-base font-medium text-destructive-foreground">
            <Phone className="h-4 w-4" /> {T.call}
          </a>
        </>
      )}
    </div>
  );
}

/** Elder mode: one plain answer at the top of a result. */
export function ElderVerdict({ result, lang }: { result: AnalysisResult; lang: Lang }) {
  const [on] = useElderMode();
  if (!on) return null;
  const level = result.verdict === "legitimate" ? "safe" : result.threat_score >= 0.7 ? "scam" : "warn";
  return <Card level={level} lang={lang} />;
}

/** Elder mode: a check that needs no typing or copy-paste, for a phone call
 * or a message someone can't copy. Rule based and stated as such. */
export function ElderQuestions({ lang }: { lang: Lang }) {
  const [on] = useElderMode();
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [done, setDone] = useState(false);
  const [copied, setCopied] = useState(false);
  if (!on) return null;
  const T = TXT[lang] ?? TXT.en;
  const level = [...ticked].some((k) => STRONG.has(k)) ? "scam" : ticked.size ? "warn" : "safe";
  const toggle = (k: string) => { setDone(false); setTicked((t) => { const n = new Set(t); if (n.has(k)) n.delete(k); else n.add(k); return n; }); };
  const note = () => {
    const picked = T.qs.filter(([k]) => ticked.has(k)).map(([, q]) => `- ${q}`).join("\n");
    const head = lang === "hi" ? "मुझे यह कॉल/मैसेज आया। ScamGuard के अनुसार:" : "I got this call/message. ScamGuard says:";
    return `${head} ${T[level]}\n${picked}\n${lang === "hi" ? "कृपया मुझसे बात करें।" : "Please call me."}`;
  };
  return (
    <section className="mb-6 rounded-lg border border-border bg-card p-5">
      <h3 className="text-lg font-semibold">{T.qTitle}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{T.qSub}</p>
      <ul className="mt-4 space-y-2">
        {T.qs.map(([k, q]) => (
          <li key={k}>
            <label className={cn("flex cursor-pointer items-start gap-3 rounded-md border p-3 text-base", ticked.has(k) ? "border-primary bg-primary/5" : "border-border")}>
              <input type="checkbox" className="mt-1 h-5 w-5 accent-[hsl(var(--primary))]" checked={ticked.has(k)} onChange={() => toggle(k)} />
              <span>{q}</span>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" onClick={() => setDone(true)} className="rounded-md bg-primary px-5 py-2.5 text-base font-medium text-primary-foreground">{T.check}</button>
        <button type="button" onClick={() => { setTicked(new Set()); setDone(false); }} className="rounded-md border border-border px-4 py-2.5 text-base">{T.clear}</button>
      </div>
      {done && (
        <div className="mt-4 space-y-3">
          <Card level={level} lang={lang} note={level === "safe" ? T.none : undefined} />
          {level !== "safe" && (
            <button type="button" onClick={async () => { try { await navigator.clipboard.writeText(note()); setCopied(true); } catch { /* clipboard blocked */ } }}
              className="rounded-md border border-border px-4 py-2 text-sm">
              {copied ? T.copied : T.family}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

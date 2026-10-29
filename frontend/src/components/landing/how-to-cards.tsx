"use client";

import { useState } from "react";
import { BookOpen, Bot, FileSearch, HeartHandshake, History, MessageSquareText, PhoneCall, ShieldCheck, Wallet, type LucideIcon } from "lucide-react";
import { useLanguage } from "@/lib/i18n/language-context";
import { cn } from "@/lib/utils";

type Card = { icon: LucideIcon; title: string; hint: string; steps: string[] };

const CARDS: Record<"en" | "hi", Card[]> = {
  en: [
    { icon: MessageSquareText, title: "Check a message", hint: "SMS, WhatsApp or email text", steps: ["Copy the message you received.", "Paste it in the quick check box on this page.", "Press Check message. No sign-up needed."] },
    { icon: ShieldCheck, title: "Read the result", hint: "Scam or genuine, and why", steps: ["The top line says Scam or Looks genuine.", "Red phrases are the traps, grouped by stage.", "TrustLens shows the evidence for and against."] },
    { icon: FileSearch, title: "Links, screenshots, calls", hint: "More than plain text", steps: ["Create a free account or use the demo account.", "Open Investigate and pick a tab, like URL, Screenshot or Voice.", "Upload or paste, then press Analyze evidence."] },
    { icon: Wallet, title: "Before you pay", hint: "Safety tools, no login", steps: ["Open Safety tools from the top menu.", "Scan a QR to see who really gets paid.", "Check a UPI request or a payment screenshot."] },
    { icon: Bot, title: "Ask Copilot", hint: "The robot at the bottom right", steps: ["Tap the robot button on any page.", "Paste a message, or ask 'is this real?'.", "Ask follow-ups like 'I already paid, what now?'."] },
    { icon: PhoneCall, title: "Already paid?", hint: "Act within the first hour", steps: ["Call 1930, the free cyber helpline, at once.", "On a scam result, tap 'I already paid' for a ready complaint.", "Report the number on Chakshu (sancharsaathi.gov.in)."] },
    { icon: HeartHandshake, title: "Elder mode", hint: "Bigger, simpler screens", steps: ["Press Elder mode in the top bar.", "No message? Tick what happened on the call.", "Copy a note and send it to your family."] },
    { icon: History, title: "Keep a record", hint: "History and reports", steps: ["Signed-in scans are saved in History.", "Download a PDF or CSV report of any scan.", "Analytics shows your scans over time."] },
  ],
  hi: [
    { icon: MessageSquareText, title: "मैसेज जाँचें", hint: "SMS, WhatsApp या ईमेल", steps: ["आया हुआ मैसेज कॉपी करें।", "इस पेज के क्विक चेक बॉक्स में पेस्ट करें।", "Check message दबाएँ। साइन-अप ज़रूरी नहीं।"] },
    { icon: ShieldCheck, title: "नतीजा समझें", hint: "धोखा या असली, और क्यों", steps: ["सबसे ऊपर लिखा होता है: धोखा या असली।", "लाल शब्द जाल हैं, चरणों में बँटे हुए।", "TrustLens पक्ष और विपक्ष के सबूत दिखाता है।"] },
    { icon: FileSearch, title: "लिंक, स्क्रीनशॉट, कॉल", hint: "सिर्फ़ टेक्स्ट नहीं", steps: ["मुफ़्त अकाउंट बनाएँ या डेमो अकाउंट लें।", "Investigate में URL, Email, Screenshot, PDF, QR या Voice चुनें।", "अपलोड या पेस्ट करके Analyze evidence दबाएँ।"] },
    { icon: Wallet, title: "पैसे भेजने से पहले", hint: "सुरक्षा टूल, बिना लॉगिन", steps: ["ऊपर मेन्यू से Safety tools खोलें।", "QR स्कैन करके देखें पैसा असल में किसे जाएगा।", "UPI अनुरोध या पेमेंट स्क्रीनशॉट जाँचें।"] },
    { icon: Bot, title: "Copilot से पूछें", hint: "नीचे दाईं ओर रोबोट", steps: ["किसी भी पेज पर रोबोट बटन दबाएँ।", "मैसेज पेस्ट करें या पूछें 'क्या यह असली है?'।", "आगे पूछें, जैसे 'पैसे भेज दिए, अब क्या?'।"] },
    { icon: PhoneCall, title: "पैसे भेज दिए?", hint: "पहले घंटे में कदम उठाएँ", steps: ["तुरंत 1930 (मुफ़्त साइबर हेल्पलाइन) पर कॉल करें।", "स्कैम नतीजे पर 'I already paid' दबाकर तैयार शिकायत लें।", "नंबर की शिकायत Chakshu (sancharsaathi.gov.in) पर करें।"] },
    { icon: HeartHandshake, title: "एल्डर मोड", hint: "बड़ी, आसान स्क्रीन", steps: ["ऊपर Elder mode दबाएँ।", "मैसेज नहीं? कॉल में जो हुआ उस पर टिक करें।", "नोट कॉपी करके परिवार को भेजें।"] },
    { icon: History, title: "रिकॉर्ड रखें", hint: "हिस्ट्री और रिपोर्ट", steps: ["लॉगिन करके किए स्कैन History में सेव रहते हैं।", "किसी भी स्कैन की PDF या CSV रिपोर्ट लें।", "Analytics में समय के साथ आपके स्कैन दिखते हैं।"] },
  ],
};

function FlipCard({ card, n, flipped, onFlip }: { card: Card; n: number; flipped: boolean; onFlip: () => void }) {
  const Icon = card.icon;
  return (
    <button
      type="button"
      onClick={onFlip}
      aria-pressed={flipped}
      aria-label={`${card.title}: ${flipped ? "hide steps" : "show steps"}`}
      className="group h-44 w-full sm:h-56 text-left [perspective:1000px] focus-visible:outline-none"
    >
      <div className={cn("relative h-full w-full rounded-xl transition-transform duration-500 [transform-style:preserve-3d] motion-reduce:transition-none", flipped && "[transform:rotateY(180deg)]")}>
        {/* front */}
        <div className="absolute inset-0 flex flex-col justify-between rounded-xl border border-border bg-card p-5 [backface-visibility:hidden] group-hover:border-primary/50 group-focus-visible:ring-2 group-focus-visible:ring-primary">
          <div className="flex items-start justify-between">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon className="h-5 w-5" /></span>
            <span className="text-xs tabular-nums text-muted-foreground">{String(n).padStart(2, "0")}</span>
          </div>
          <div>
            <p className="text-base font-semibold text-foreground">{card.title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{card.hint}</p>
          </div>
        </div>
        {/* back */}
        <div className="absolute inset-0 rounded-xl border border-primary/40 bg-card p-5 [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <p className="text-sm font-semibold text-foreground">{card.title}</p>
          <ol className="mt-3 space-y-2">
            {card.steps.map((s, i) => (
              <li key={i} className="flex gap-2.5 text-[13px] leading-snug text-foreground">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground">{i + 1}</span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </button>
  );
}

/** "How to use ScamGuard": eight flip cards, each with three short steps. */
export function HowToCards() {
  const { lang } = useLanguage();
  const cards = CARDS[lang] ?? CARDS.en;
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (i: number) => setOpen((o) => { const n = new Set(o); if (n.has(i)) n.delete(i); else n.add(i); return n; });
  const allOpen = open.size === cards.length;
  return (
    <section id="how-to-use" className="scroll-mt-20 border-t border-border px-6 py-16">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-sm font-medium text-primary"><BookOpen className="h-4 w-4" /> {lang === "hi" ? "कैसे इस्तेमाल करें" : "How to use ScamGuard"}</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{lang === "hi" ? "हर काम, तीन आसान कदम में" : "Everything it does, in three steps each"}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{lang === "hi" ? "किसी कार्ड पर टैप करें, कदम दिखेंगे।" : "Tap a card to flip it and see the steps."}</p>
          </div>
          <button type="button" onClick={() => setOpen(allOpen ? new Set() : new Set(cards.map((_, i) => i)))} className="text-sm font-medium text-primary hover:underline">
            {allOpen ? (lang === "hi" ? "सभी बंद करें" : "Flip all back") : (lang === "hi" ? "सभी कदम दिखाएँ" : "Show all steps")}
          </button>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c, i) => <FlipCard key={c.title} card={c} n={i + 1} flipped={open.has(i)} onFlip={() => toggle(i)} />)}
        </div>
      </div>
    </section>
  );
}

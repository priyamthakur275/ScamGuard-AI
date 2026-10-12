import { MessagesSquare } from "lucide-react";

interface ChatMeta {
  incoming?: string[];
  outgoing?: string[];
  header?: string | null;
}

/** Shows how a chat screenshot was read: the sender's lines (scored) vs the user's own replies. */
export function ChatPanel({ chat }: { chat: ChatMeta | null | undefined }) {
  if (!chat || (!chat.incoming?.length && !chat.outgoing?.length)) return null;
  return (
    <div className="border border-border p-5">
      <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wide text-foreground">
        <MessagesSquare className="h-3.5 w-3.5 text-primary" />
        Chat screenshot{chat.header ? ` · ${chat.header}` : ""}
      </p>
      <div className="flex flex-col gap-2 text-sm">
        {(chat.incoming ?? []).map((line, i) => (
          <p key={`in-${i}`} className="max-w-[85%] self-start border border-border bg-muted/40 px-3 py-1.5">{line}</p>
        ))}
        {(chat.outgoing ?? []).map((line, i) => (
          <p key={`out-${i}`} className="max-w-[85%] self-end border border-primary/30 bg-primary/10 px-3 py-1.5 text-muted-foreground">{line}</p>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        Left: the sender&apos;s messages (these were scored). Right: your replies (ignored).
      </p>
    </div>
  );
}

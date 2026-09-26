import { Fragment, type ReactNode } from "react";

/** Renders the small subset of Markdown the assistant uses (**bold**, "- " / "* " bullets,
 * line breaks) as React elements. No HTML injection: model text is never set as innerHTML. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  );
}

export function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let bullets: string[] = [];
  const flush = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="my-1 list-disc space-y-0.5 pl-5">
          {bullets.map((b, i) => (
            <li key={i}>{inline(b)}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  };
  for (const line of text.split("\n")) {
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    if (bullet) {
      bullets.push(bullet[1]);
      continue;
    }
    flush();
    // Short "Label:" lines (e.g. "Pros:", "खूबियाँ:") read as mini headings.
    const label = /^[^:]{1,24}:$/.test(line.trim());
    if (line.trim()) blocks.push(<p key={`p-${blocks.length}`} className={label ? "font-semibold" : undefined}>{inline(line)}</p>);
  }
  flush();
  return <div className="space-y-1.5">{blocks}</div>;
}

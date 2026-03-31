import type { ReactNode } from "react";

type MarkdownTextProps = {
  text: string;
};

function coerceCitationContinuations(text: string): string {
  const lines = text.split("\n");
  const normalized: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      normalized.push("");
      continue;
    }

    const isListLine = /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line);
    const isHeadingLine = /^(#{1,3})\s+/.test(line);
    const hasCitation = /\[Source:[^\]]+\]/i.test(line);
    const previous = normalized.length > 0 ? normalized[normalized.length - 1].trim() : "";
    const previousIsList = /^[-*]\s+/.test(previous);

    if (!isListLine && !isHeadingLine && hasCitation && previousIsList) {
      normalized.push(`- ${line}`);
      continue;
    }

    normalized.push(line);
  }

  return normalized.join("\n");
}

function normalizeBrokenLabelSections(text: string): string {
  const withLabelBreaks = text
    .replace(/\s(?=\*\*[A-Z][A-Za-z0-9 '&()/.\-]{1,48}:\*-?)/g, "\n")
    .replace(/\*\*([A-Za-z][A-Za-z0-9 '&()/.\-]{1,48}):\*\s*-\s*/g, "- **$1:** ")
    .replace(/\*\*([A-Za-z][A-Za-z0-9 '&()/.\-]{1,48}):\*-\s*/g, "- **$1:** ")
    .replace(/\*\*([A-Za-z][A-Za-z0-9 '&()/.\-]{1,48}):\*/g, "- **$1:** ")
    .replace(/^-\s+\*\*([^*\n]+):\*\*\s*-\s*/gm, "- **$1:** ")
    .replace(/^-\s+-\s+/gm, "- ");

  const lines = withLabelBreaks.split("\n");
  const normalized: string[] = [];
  let labelContextActive = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      normalized.push("");
      labelContextActive = false;
      continue;
    }

    const isHeading = /^(#{1,3})\s+/.test(line);
    const isList = /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line);
    const isLabelHeader = /^-\s+\*\*[^*\n]+:\*\*/.test(line);
    const startsNewBrokenLabel = /^\*\*[A-Za-z][A-Za-z0-9 '&()/.\-]{1,48}:/.test(line);

    if (startsNewBrokenLabel) {
      const repaired = line
        .replace(/^\*\*([A-Za-z][A-Za-z0-9 '&()/.\-]{1,48}):\*?\s*-?\s*/, "- **$1:** ")
        .replace(/^-\s+-\s+/, "- ");
      normalized.push(repaired);
      labelContextActive = true;
      continue;
    }

    if (labelContextActive && !isHeading && !isList) {
      normalized.push(`- ${line}`);
      continue;
    }

    normalized.push(line);
    labelContextActive = isLabelHeader;
  }

  return normalized.join("\n");
}

function normalizeMarkdown(text: string): string {
  let normalized = text.replace(/\r\n/g, "\n").trim();
  normalized = normalizeBrokenLabelSections(normalized);
  normalized = normalized.replace(/:\s+\*\s+/g, ":\n* ");
  normalized = normalized.replace(/\.\s+\*\s+/g, ".\n* ");
  normalized = normalized.replace(/\]\s+\*\s+/g, "]\n* ");
  normalized = normalized.replace(/:\s+-\s+/g, ":\n- ");
  normalized = normalized.replace(/\.\s+-\s+/g, ".\n- ");
  normalized = normalized.replace(/\]\s+-\s+/g, "]\n- ");
  normalized = normalized.replace(/\*\s+/g, "- ");
  normalized = normalized.replace(/\n\s*[-*]\s*Document Types:\s*/gi, "\n- **Document Types:** ");
  normalized = normalized.replace(/\n\s*[-*]\s*Case:\s*/gi, "\n- **Case:** ");
  normalized = normalized.replace(/\n\s*[-*]\s*Supporting details:\s*/gi, "\n\n### Supporting details\n");
  normalized = normalized.replace(
    /(^|\n)([A-Za-z][A-Za-z0-9\s\-()\/]+):\s+([^\n]+(?:\n(?![A-Za-z][A-Za-z0-9\s\-()\/]+:\s+)[^\n]+)*)/g,
    (_match, prefix, label, value) => {
      const cleanedLabel = String(label).trim();
      const cleanedValue = String(value).trim().replace(/\n+/g, " ");
      if (cleanedLabel.length > 48 || !cleanedValue) {
        return `${prefix}${cleanedLabel}: ${cleanedValue}`;
      }
      return `${prefix}- **${cleanedLabel}:** ${cleanedValue}`;
    },
  );
  normalized = coerceCitationContinuations(normalized);
  normalized = normalized.replace(/^\s*[-*]\s+$/gm, "");
  normalized = normalized.replace(/\n{3,}/g, "\n\n");
  return normalized;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  const nodes: ReactNode[] = [];

  for (let index = 0; index < parts.length; index += 1) {
    const part = parts[index];
    if (!part) {
      continue;
    }

    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      nodes.push(
        <strong key={`${keyPrefix}-strong-${index}`}>
          {part.slice(2, -2)}
        </strong>,
      );
      continue;
    }

    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      nodes.push(
        <code key={`${keyPrefix}-code-${index}`} className="chat-inline-code">
          {part.slice(1, -1)}
        </code>,
      );
      continue;
    }

    nodes.push(<span key={`${keyPrefix}-text-${index}`}>{part}</span>);
  }

  return nodes;
}

export default function MarkdownText({ text }: MarkdownTextProps) {
  const normalized = normalizeMarkdown(text);
  if (!normalized) {
    return null;
  }

  const lines = normalized.split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const raw = lines[index];
    const line = raw.trim();

    if (!line) {
      index += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      blocks.push(
        <h3 key={`heading-${index}`} className="chat-md-heading">
          {renderInline(headingMatch[2], `heading-${index}`)}
        </h3>,
      );
      index += 1;
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.+)$/);
    if (unorderedMatch) {
      const items: string[] = [];
      const seen = new Set<string>();
      while (index < lines.length) {
        const candidate = lines[index].trim();
        const match = candidate.match(/^[-*]\s+(.+)$/);
        if (!match) {
          break;
        }
        const itemText = match[1];
        const dedupeKey = itemText
          .replace(/\[Source:[^\]]+\]/gi, "")
          .replace(/\s+/g, " ")
          .trim()
          .toLowerCase();
        if (dedupeKey && !seen.has(dedupeKey)) {
          seen.add(dedupeKey);
          items.push(itemText);
        }
        index += 1;
      }

      blocks.push(
        <ul key={`ul-${index}`} className="chat-md-list">
          {items.map((item, itemIndex) => (
            <li key={`ul-${index}-${itemIndex}`}>
              {renderInline(item, `ul-${index}-${itemIndex}`)}
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (orderedMatch) {
      const items: string[] = [];
      while (index < lines.length) {
        const candidate = lines[index].trim();
        const match = candidate.match(/^\d+\.\s+(.+)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
        index += 1;
      }

      blocks.push(
        <ol key={`ol-${index}`} className="chat-md-list ordered">
          {items.map((item, itemIndex) => (
            <li key={`ol-${index}-${itemIndex}`}>
              {renderInline(item, `ol-${index}-${itemIndex}`)}
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    const paragraphLines: string[] = [line];
    index += 1;
    while (index < lines.length) {
      const candidate = lines[index].trim();
      if (!candidate) {
        index += 1;
        break;
      }
      if (
        candidate.match(/^(#{1,3})\s+/) ||
        candidate.match(/^[-*]\s+/) ||
        candidate.match(/^\d+\.\s+/)
      ) {
        break;
      }
      paragraphLines.push(candidate);
      index += 1;
    }

    const paragraph = paragraphLines.join(" ");
    blocks.push(
      <p key={`p-${index}`} className="chat-md-paragraph">
        {renderInline(paragraph, `p-${index}`)}
      </p>,
    );
  }

  return <div className="chat-markdown">{blocks}</div>;
}

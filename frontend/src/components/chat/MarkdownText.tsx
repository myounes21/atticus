import type { ReactNode } from "react";

type MarkdownTextProps = {
  text: string;
};

function normalizeMarkdown(text: string): string {
  let normalized = text.replace(/\r\n/g, "\n").trim();
  normalized = normalized.replace(/:\s+\*\s+/g, ":\n* ");
  normalized = normalized.replace(/\.\s+\*\s+/g, ".\n* ");
  normalized = normalized.replace(/\]\s+\*\s+/g, "]\n* ");
  normalized = normalized.replace(/:\s+-\s+/g, ":\n- ");
  normalized = normalized.replace(/\.\s+-\s+/g, ".\n- ");
  normalized = normalized.replace(/\]\s+-\s+/g, "]\n- ");
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
      while (index < lines.length) {
        const candidate = lines[index].trim();
        const match = candidate.match(/^[-*]\s+(.+)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
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

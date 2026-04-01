import { useEffect, useId, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";

type MarkdownTextProps = {
  text: string;
};

function normalizeMarkdown(text: string): string {
  return text.replace(/\r\n/g, "\n").trim();
}

function escapeHtmlAttribute(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function injectSources(text: string): string {
  const regex = /\[Source: ([^\]]+)\]/g;
  return text.replace(regex, (_fullMatch, source: string) => {
    const escapedSource = escapeHtmlAttribute(source);
    return `<source data="${escapedSource}" />`;
  });
}

type SourceTooltipProps = {
  content: string;
};

function SourceTooltip({ content }: SourceTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const wrapperRef = useRef<HTMLSpanElement | null>(null);
  const tooltipId = useId();
  const isVisible = isOpen || isHovered;

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);

    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [isOpen]);

  return (
    <span
      ref={wrapperRef}
      className="relative mx-1 inline-flex align-middle"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <button
        type="button"
        className="material-symbols-outlined cursor-pointer text-[16px] text-primary/60 transition-colors hover:text-primary focus-visible:text-primary focus-visible:outline-none"
        aria-label="Show source details"
        aria-expanded={isVisible}
        aria-describedby={tooltipId}
        onClick={() => setIsOpen((prev) => !prev)}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setIsOpen(false);
            event.currentTarget.blur();
          }
        }}
      >
        info
      </button>
      <span
        id={tooltipId}
        role="tooltip"
        className={`pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-64 max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-lg border border-outline-variant/40 bg-surface-container px-3 py-2 text-xs text-on-surface shadow-md ${isVisible ? "block" : "hidden"}`}
      >
        {content}
      </span>
    </span>
  );
}

export default function MarkdownText({ text }: MarkdownTextProps) {
  const normalized = normalizeMarkdown(text);
  if (!normalized) {
    return null;
  }

  const markdown = injectSources(normalized);

  return (
    <div className="space-y-2 text-sm leading-relaxed text-on-surface">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          h1: ({ children }) => <h3 className="text-sm font-semibold text-on-surface">{children}</h3>,
          h2: ({ children }) => <h3 className="text-sm font-semibold text-on-surface">{children}</h3>,
          h3: ({ children }) => <h3 className="text-sm font-semibold text-on-surface">{children}</h3>,
          p: ({ children }) => <p className="whitespace-pre-wrap text-on-surface-variant">{children}</p>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5 text-on-surface-variant">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5 text-on-surface-variant">{children}</ol>,
          code: ({ className, children }) => {
            const content = String(children).replace(/\n$/, "");
            if (!className) {
              return <code className="rounded border border-outline-variant/50 bg-surface-container-low px-1.5 py-0.5 text-[0.85em]">{content}</code>;
            }
            return (
              <pre className="overflow-x-auto rounded-lg bg-surface-container-low p-3 text-xs">
                <code className={className}>{content}</code>
              </pre>
            );
          },
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-primary-alt underline underline-offset-2">
              {children}
            </a>
          ),
          source: ({ node }) => {
            const data = node?.properties?.data;
            const content = typeof data === "string" ? data : "";
            return <SourceTooltip content={content} />;
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/40 pl-3 text-on-surface-variant">{children}</blockquote>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

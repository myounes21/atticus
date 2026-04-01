import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type MarkdownTextProps = {
  text: string;
};

function normalizeMarkdown(text: string): string {
  return text.replace(/\r\n/g, "\n").trim();
}

export default function MarkdownText({ text }: MarkdownTextProps) {
  const normalized = normalizeMarkdown(text);
  if (!normalized) {
    return null;
  }

  return (
    <div className="space-y-2 text-sm leading-relaxed text-on-surface">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="text-sm font-semibold text-on-surface">{children}</h3>,
          h2: ({ children }) => <h3 className="text-sm font-semibold text-on-surface">{children}</h3>,
          h3: ({ children }) => <h3 className="text-sm font-semibold text-on-surface">{children}</h3>,
          p: ({ children }) => <p className="whitespace-pre-wrap text-on-surface-variant">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 text-on-surface-variant">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1 text-on-surface-variant">{children}</ol>,
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
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/40 pl-3 text-on-surface-variant">{children}</blockquote>
          ),
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
}

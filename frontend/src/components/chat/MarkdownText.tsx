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
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="chat-md-heading">{children}</h3>,
          h2: ({ children }) => <h3 className="chat-md-heading">{children}</h3>,
          h3: ({ children }) => <h3 className="chat-md-heading">{children}</h3>,
          p: ({ children }) => <p className="chat-md-paragraph">{children}</p>,
          ul: ({ children }) => <ul className="chat-md-list">{children}</ul>,
          ol: ({ children }) => <ol className="chat-md-list ordered">{children}</ol>,
          code: ({ className, children }) => {
            const content = String(children).replace(/\n$/, "");
            if (!className) {
              return <code className="chat-inline-code">{content}</code>;
            }
            return (
              <pre className="chat-code-block">
                <code className={className}>{content}</code>
              </pre>
            );
          },
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="chat-md-link">
              {children}
            </a>
          ),
          blockquote: ({ children }) => <blockquote className="chat-md-quote">{children}</blockquote>,
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
}

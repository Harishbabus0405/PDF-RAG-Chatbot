import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Safe, dependency-free Markdown renderer for LLM responses.
 * Parses standard Markdown syntax into React elements without dangerouslySetInnerHTML.
 */
export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const elements = parseMarkdown(content);
  return (
    <div
      className={`prose prose-slate dark:prose-invert max-w-none text-xs sm:text-sm leading-relaxed space-y-3 ${className}`}
    >
      {elements}
    </div>
  );
}

function parseMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];

  // Normalize line endings
  const normalized = text.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  const nodes: React.ReactNode[] = [];

  let inCodeBlock = false;
  let codeBlockLang = "";
  let codeBlockLines: string[] = [];
  let inList = false;
  let listType: "ul" | "ol" = "ul";
  let listItems: React.ReactNode[] = [];
  let inBlockquote = false;
  let blockquoteLines: string[] = [];

  const flushCodeBlock = (key: string) => {
    if (codeBlockLines.length > 0 || inCodeBlock) {
      const codeString = codeBlockLines.join("\n");
      nodes.push(
        <CodeBlock
          key={key}
          code={codeString}
          language={codeBlockLang}
        />
      );
      codeBlockLines = [];
      codeBlockLang = "";
      inCodeBlock = false;
    }
  };

  const flushList = (key: string) => {
    if (listItems.length > 0) {
      if (listType === "ul") {
        nodes.push(
          <ul
            key={key}
            className="my-2 ml-4 list-disc space-y-1 text-slate-700 dark:text-slate-300"
          >
            {listItems}
          </ul>
        );
      } else {
        nodes.push(
          <ol
            key={key}
            className="my-2 ml-4 list-decimal space-y-1 text-slate-700 dark:text-slate-300"
          >
            {listItems}
          </ol>
        );
      }
      listItems = [];
      inList = false;
    }
  };

  const flushBlockquote = (key: string) => {
    if (blockquoteLines.length > 0) {
      nodes.push(
        <blockquote
          key={key}
          className="my-2 border-l-4 border-violet-500/50 pl-3 italic text-slate-600 dark:text-slate-400 bg-violet-500/5 py-1 rounded-r-md"
        >
          {blockquoteLines.map((line, idx) => (
            <p key={idx}>{renderInlineMarkdown(line)}</p>
          ))}
        </blockquote>
      );
      blockquoteLines = [];
      inBlockquote = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle (```)
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        flushCodeBlock(`code-block-${i}`);
      } else {
        // Flush any active list or blockquote before code block
        flushList(`list-before-code-${i}`);
        flushBlockquote(`quote-before-code-${i}`);
        inCodeBlock = true;
        codeBlockLang = line.trim().slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Blockquote
    if (line.startsWith(">")) {
      flushList(`list-before-quote-${i}`);
      inBlockquote = true;
      blockquoteLines.push(line.replace(/^>\s?/, ""));
      continue;
    } else if (inBlockquote) {
      flushBlockquote(`quote-${i}`);
    }

    // Unordered List item (- or * followed by space)
    const ulMatch = line.match(/^(\s*)[-*]\s+(.+)$/);
    if (ulMatch) {
      if (inList && listType !== "ul") {
        flushList(`switch-list-${i}`);
      }
      inList = true;
      listType = "ul";
      listItems.push(
        <li key={`ul-item-${i}`} className="pl-1 leading-relaxed">
          {renderInlineMarkdown(ulMatch[2])}
        </li>
      );
      continue;
    }

    // Ordered List item (1. 2. etc.)
    const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
    if (olMatch) {
      if (inList && listType !== "ol") {
        flushList(`switch-list-${i}`);
      }
      inList = true;
      listType = "ol";
      listItems.push(
        <li key={`ol-item-${i}`} className="pl-1 leading-relaxed">
          {renderInlineMarkdown(olMatch[2])}
        </li>
      );
      continue;
    }

    // If we reach a non-list line, flush active list
    if (inList) {
      flushList(`list-end-${i}`);
    }

    // Empty line
    if (!line.trim()) {
      continue;
    }

    // Headings
    if (line.startsWith("#### ")) {
      nodes.push(
        <h5
          key={`h4-${i}`}
          className="text-xs font-bold uppercase tracking-wide text-slate-800 dark:text-slate-200 mt-3 mb-1"
        >
          {renderInlineMarkdown(line.slice(5))}
        </h5>
      );
      continue;
    }
    if (line.startsWith("### ")) {
      nodes.push(
        <h4
          key={`h3-${i}`}
          className="text-sm font-bold text-slate-900 dark:text-white mt-3.5 mb-1 text-violet-700 dark:text-violet-300"
        >
          {renderInlineMarkdown(line.slice(4))}
        </h4>
      );
      continue;
    }
    if (line.startsWith("## ")) {
      nodes.push(
        <h3
          key={`h2-${i}`}
          className="text-base font-bold text-slate-900 dark:text-white mt-4 mb-1.5"
        >
          {renderInlineMarkdown(line.slice(3))}
        </h3>
      );
      continue;
    }
    if (line.startsWith("# ")) {
      nodes.push(
        <h2
          key={`h1-${i}`}
          className="text-lg font-bold text-slate-900 dark:text-white mt-4 mb-2"
        >
          {renderInlineMarkdown(line.slice(2))}
        </h2>
      );
      continue;
    }

    // Horizontal Rule
    if (line.trim() === "---" || line.trim() === "***" || line.trim() === "___") {
      nodes.push(
        <hr
          key={`hr-${i}`}
          className="my-3 border-slate-200 dark:border-white/10"
        />
      );
      continue;
    }

    // Regular Paragraph
    nodes.push(
      <p key={`p-${i}`} className="my-1.5 leading-relaxed text-slate-800 dark:text-slate-200">
        {renderInlineMarkdown(line)}
      </p>
    );
  }

  // Flush remaining blocks
  if (inCodeBlock) flushCodeBlock("code-end");
  if (inList) flushList("list-end");
  if (inBlockquote) flushBlockquote("quote-end");

  return nodes;
}

/**
 * Parses inline formatting: bold, italic, inline code, and URLs.
 */
function renderInlineMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];

  const tokens: React.ReactNode[] = [];
  // Regex to split on code blocks, bold, italics
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)/g;
  const parts = text.split(regex);

  parts.forEach((part, index) => {
    if (!part) return;

    // Inline code: `code`
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      tokens.push(
        <code
          key={`code-${index}`}
          className="rounded px-1.5 py-0.5 font-mono text-[11px] sm:text-xs font-semibold bg-violet-500/10 text-violet-700 dark:text-violet-300 border border-violet-500/20"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    // Bold: **text** or __text__
    else if (
      (part.startsWith("**") && part.endsWith("**") && part.length > 4) ||
      (part.startsWith("__") && part.endsWith("__") && part.length > 4)
    ) {
      tokens.push(
        <strong
          key={`strong-${index}`}
          className="font-bold text-slate-900 dark:text-white"
        >
          {part.slice(2, -2)}
        </strong>
      );
    }
    // Italic: *text* or _text_
    else if (
      (part.startsWith("*") && part.endsWith("*") && part.length > 2) ||
      (part.startsWith("_") && part.endsWith("_") && part.length > 2)
    ) {
      tokens.push(
        <em key={`em-${index}`} className="italic text-slate-700 dark:text-slate-300">
          {part.slice(1, -1)}
        </em>
      );
    } else {
      tokens.push(part);
    }
  });

  return tokens;
}

/**
 * Beautiful formatted CodeBlock with copy button and language badge.
 */
function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 overflow-hidden rounded-xl border border-slate-200 dark:border-white/10 bg-slate-900 text-slate-100 shadow-md">
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 px-3.5 py-1.5 text-xs text-slate-400">
        <span className="font-mono text-[11px] uppercase tracking-wider text-violet-400">
          {language || "code"}
        </span>
        <button
          onClick={handleCopy}
          aria-label="Copy code to clipboard"
          className="flex items-center gap-1 rounded px-2 py-0.5 text-[11px] hover:bg-white/10 transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="overflow-x-auto p-3.5 font-mono text-[11px] sm:text-xs leading-relaxed">
        <pre className="m-0 p-0">{code}</pre>
      </div>
    </div>
  );
}

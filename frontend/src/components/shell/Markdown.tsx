import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '../../lib/cn'

const components: Components = {
  h1: ({ node: _node, className, ...props }) => (
    <h1 className={cn('mt-5 text-[17px] font-semibold leading-6 first:mt-0', className)} {...props} />
  ),
  h2: ({ node: _node, className, ...props }) => (
    <h2 className={cn('mt-5 text-[15px] font-semibold leading-6 first:mt-0', className)} {...props} />
  ),
  h3: ({ node: _node, className, ...props }) => (
    <h3 className={cn('mt-4 text-[13px] font-semibold leading-6 first:mt-0', className)} {...props} />
  ),
  p: ({ node: _node, className, ...props }) => (
    <p className={cn('mt-3 break-words first:mt-0', className)} {...props} />
  ),
  ul: ({ node: _node, className, ...props }) => (
    <ul className={cn('mt-3 list-disc space-y-1 pl-5 first:mt-0', className)} {...props} />
  ),
  ol: ({ node: _node, className, ...props }) => (
    <ol className={cn('mt-3 list-decimal space-y-1 pl-5 first:mt-0', className)} {...props} />
  ),
  li: ({ node: _node, className, ...props }) => (
    <li
      className={cn('pl-0.5 [&.task-list-item]:list-none [&_input]:mr-2 [&>p]:mt-0', className)}
      {...props}
    />
  ),
  a: ({ node: _node, className, ...props }) => (
    <a
      className={cn('text-focus underline decoration-focus/35 underline-offset-2 hover:decoration-focus', className)}
      rel="noreferrer"
      target="_blank"
      {...props}
    />
  ),
  blockquote: ({ node: _node, className, ...props }) => (
    <blockquote
      className={cn('mt-3 border-l-2 border-hairline pl-3 text-muted first:mt-0', className)}
      {...props}
    />
  ),
  hr: ({ node: _node, className, ...props }) => (
    <hr className={cn('my-4 border-0 border-t border-hairline', className)} {...props} />
  ),
  pre: ({ node: _node, className, ...props }) => (
    <pre
      className={cn(
        'mt-3 max-w-full overflow-x-auto rounded-[10px] bg-[#161615] px-3 py-2.5 font-mono text-[11px] leading-5 text-[#eceae4] first:mt-0 [&>code]:bg-transparent [&>code]:p-0 [&>code]:text-inherit',
        className,
      )}
      {...props}
    />
  ),
  code: ({ node: _node, className, ...props }) => (
    <code
      className={cn('rounded bg-well px-1 py-0.5 font-mono text-[0.92em]', className)}
      {...props}
    />
  ),
  table: ({ node: _node, className, ...props }) => (
    <div className="mt-3 max-w-full overflow-x-auto rounded-[10px] ring-1 ring-line first:mt-0">
      <table className={cn('w-full border-collapse text-left', className)} {...props} />
    </div>
  ),
  th: ({ node: _node, className, ...props }) => (
    <th
      className={cn('border-b border-hairline bg-canvas px-3 py-2 font-medium', className)}
      {...props}
    />
  ),
  td: ({ node: _node, className, ...props }) => (
    <td className={cn('border-t border-hairline px-3 py-2 align-top', className)} {...props} />
  ),
}

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn('text-[13px] leading-6 text-ink', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

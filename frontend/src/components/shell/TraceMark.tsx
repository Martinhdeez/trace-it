import lightMark from '../../assets/trace-mark-clear.png'
import darkMark from '../../assets/trace-mark-dark.png'
import { cn } from '../../lib/cn'
import { useTheme } from '../../state/theme'

/** The same theme-aware character in the landing, footer, sidebar and mobile app bar. */
export function TraceMark({ className, alt = '' }: { className?: string; alt?: string }) {
  const { theme } = useTheme()
  return (
    <img
      src={theme === 'dark' ? darkMark : lightMark}
      alt={alt}
      width={256}
      height={256}
      draggable={false}
      className={cn('shrink-0 select-none object-contain', className)}
    />
  )
}

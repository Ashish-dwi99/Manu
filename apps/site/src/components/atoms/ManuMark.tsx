import { cn } from '@/lib/cn';

/**
 * Manu's mark, the same one the diary draws in its rail: the M as one
 * stroke, orange on ink. It keeps its own ground on paper and on navy alike,
 * so there is no inverse version to keep in step.
 */
export function ManuMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={cn('manu-mark', className)} viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <rect width="64" height="64" rx="14" fill="#121313" />
      <path d="M16 46V20l16 15 16-15v26" fill="none" stroke="#ea884b" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

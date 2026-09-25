import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export function Eyebrow({ children, inverse = false, className }: { children: ReactNode; inverse?: boolean; className?: string }) {
  return <p className={cn('eyebrow', inverse && 'eyebrow--inverse', className)}>{children}</p>;
}

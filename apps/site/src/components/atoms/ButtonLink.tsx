import type { AnchorHTMLAttributes, ReactNode } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { cn } from '@/lib/cn';

type ButtonLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  children: ReactNode;
  tone?: 'ink' | 'paper' | 'outline' | 'accent';
  arrow?: boolean;
};

export function ButtonLink({ children, tone = 'ink', arrow = true, className, ...props }: ButtonLinkProps) {
  return (
    <a className={cn('button-link', `button-link--${tone}`, className)} {...props}>
      <span>{children}</span>
      {arrow ? <ArrowUpRight size={16} strokeWidth={1.8} aria-hidden="true" /> : null}
    </a>
  );
}

import { cn } from '@/lib/cn';

const MANU_DOT = '#4f87b6';

/**
 * The Manu mark on its own: the joined M and the dot before it.
 *
 * The M takes `currentColor`, so any ground inverts it with one `color`
 * rule, and the dot keeps its fixed blue on either, as Tura's does. No ground
 * of its own: it sits on whatever is behind it.
 */
export function ManuMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={cn('manu-mark', className)} fill="none" viewBox="208 319 838 606" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M441 323 A111 111 0 0 1 552 420 C562 490 585 555 628 583 C650 597 665 598 676 597 C700 596 730 585 752 555 C780 515 800 465 806 425 A111 111 0 1 1 1001 508 C975 545 948 585 946 635 C944 690 975 725 1000 742 A100 100 0 1 1 846 792 C850 745 885 700 885 640 C885 595 858 560 822 560 C788 560 765 590 765 630 C765 650 770 665 768 678 A81 81 0 0 1 606 682 C604 640 595 597 560 597 C532 597 524 630 525 655 C527 700 548 740 576 766 A85 85 0 1 1 441 812 C440 790 445 768 456 745 C470 705 480 680 480 655 C480 590 445 555 400 535 A111 111 0 0 1 441 323 Z"
        fill="currentColor"
      />
      <circle cx="302" cy="818" r="90" fill={MANU_DOT} />
    </svg>
  );
}

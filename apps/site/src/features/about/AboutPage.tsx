import { FileSearch, Landmark, Scale, UsersRound } from 'lucide-react';

import { ButtonLink } from '@/components/atoms/ButtonLink';
import { ManuMark } from '@/components/atoms/ManuMark';
import { SiteFooter } from '@/components/organisms/SiteFooter';
import { SiteHeader } from '@/components/organisms/SiteHeader';
import { APP_CTA, APP_URL, CONTACT_EMAIL } from '@/config/site';
import { LabNote } from '@/features/about/LabNote';
import { WorkCorridor } from '@/features/about/WorkCorridor';

/** What we hold to: four cards, each banded in one of the product tour's tones. */
const PRECEPTS = [
  {
    icon: FileSearch,
    tone: 'blue',
    title: 'The record comes first',
    copy: 'Every fact is traced to the order, the page and the words. What cannot be traced is shown as a gap, never filled with a guess.',
  },
  {
    icon: Scale,
    tone: 'terracotta',
    title: 'Liberty cannot wait',
    copy: 'A missed date costs someone their days. The custody arithmetic is shown to the defence and the bench alike, with its working.',
  },
  {
    icon: Landmark,
    tone: 'olive',
    title: 'The court decides',
    copy: 'No predictions, no scores for accused persons, no analytics about judges. Manu supports the people who decide and never leans on them.',
  },
  {
    icon: UsersRound,
    tone: 'saffron',
    title: 'People act',
    copy: 'Manu prepares the draft and the message. A person reads it, files it and sends it. Nothing Manu does is irreversible.',
  },
] as const;

/** Who makes Manu: the work, a note on why, what we hold to, and a way in. */
export function AboutPage() {
  return (
    <div className="about-page" id="top">
      <SiteHeader />
      <main>
        <section className="about-hero">
          <div className="about-hero__copy">
            <p className="about-kicker">About</p>
            <h1>Hi, we&rsquo;re <em>Sankhya AI Labs.</em></h1>
            <p>
              We build Manu, the case diary that reads the court for Indian advocates, firms and judges, because justice
              runs on the record and the record should never be the thing that is missed.
            </p>
          </div>
        </section>

        <WorkCorridor />
        <LabNote />

        <section className="about-precepts about-precepts--values" aria-labelledby="about-precepts-title">
          <header className="about-precepts__head">
            <p className="about-kicker">What we hold to</p>
            <h2 id="about-precepts-title">The principles <em>behind the product.</em></h2>
          </header>
          <div className="about-precepts__grid">
            {PRECEPTS.map(({ icon: Icon, tone, title, copy }) => (
              <article className={`about-precept tone-${tone}`} key={title}>
                <span className="about-precept__band" aria-hidden="true">
                  <span className="about-precept__icon"><Icon size={22} strokeWidth={1.7} /></span>
                </span>
                <div className="about-precept__body">
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="about-lab" aria-labelledby="about-lab-title">
          <div>
            <p className="about-kicker">The lab</p>
            <h2 id="about-lab-title">Careful AI, <em>for work that matters.</em></h2>
          </div>
          <div>
            <p>
              Sankhya AI Labs builds the infrastructure AI needs to be trusted with serious work: what it should
              remember, what it should look at, and what must wait for a person&rsquo;s approval.
            </p>
            <p>
              Manu is where that work meets the courts. Write to us at{' '}
              <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>, whether you practise, run a chamber, sit on the
              bench, or want to help build it.
            </p>
          </div>
        </section>

        <section className="about-final" aria-labelledby="about-final-title">
          <div className="about-final__rings" aria-hidden="true" />
          <h2 id="about-final-title">Justice should never wait <em>on a date nobody saw.</em></h2>
          <span className="about-final__mark" aria-hidden="true"><ManuMark /></span>
          <p>Bring a CNR. Tomorrow morning, Manu will have read the court.</p>
          <ButtonLink href={APP_URL} tone="paper">{APP_CTA}</ButtonLink>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

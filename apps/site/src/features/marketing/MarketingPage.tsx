import { BellRing, CalendarClock, Check, CheckCircle2, EyeOff, FileSearch, Hash, ListChecks, Quote, Scale, ShieldCheck, UserSearch } from 'lucide-react';

import { ButtonLink } from '@/components/atoms/ButtonLink';
import { Eyebrow } from '@/components/atoms/Eyebrow';
import { PaperThreads } from '@/components/atoms/PaperThreads';
import { DiaryPreview } from '@/components/molecules/DiaryPreview';
import { PaperGround } from '@/components/molecules/PaperGround';
import { ProductTour } from '@/components/molecules/ProductTour';
import { SiteFooter } from '@/components/organisms/SiteFooter';
import { SiteHeader } from '@/components/organisms/SiteHeader';
import { APP_CTA, APP_CTA_FIRST, APP_URL } from '@/config/site';
import { useHashScroll } from '@/hooks/useHashScroll';

/** The six labels on the cause list, in the words the case page uses. */
const LIBERTY_LABELS = [
  ['479 ALERT', 'Someone in custody is near or past the Section 479 BNSS threshold.'],
  ['URGENT', 'Default bail is about to accrue, or already has.'],
  ['BAIL', 'The matter is listed for a bail hearing.'],
  ['WOMAN', 'A woman is in custody.'],
  ['JUVENILE', 'The record says the accused is a juvenile.'],
  ['DATA GAP', 'A charge Manu could not match to an offence. Shown, not guessed.'],
] as const;

const PRINCIPLES = [
  {
    tone: 'blue',
    icon: Quote,
    title: 'Every fact has a source.',
    body: 'The order, the page and the words, on every line, and whether the court said it, a person confirmed it, or Manu only read it.',
  },
  {
    tone: 'olive',
    icon: Scale,
    title: 'The law is code, not a model.',
    body: 'Section 479, default bail and limitation are fixed rules with the working shown. No model does the arithmetic.',
  },
  {
    tone: 'terracotta',
    icon: ShieldCheck,
    title: 'Nothing it cannot take back.',
    body: 'No filing, no payment, no portal submission and no message to anyone. Those tools do not exist in Manu.',
  },
  {
    tone: 'saffron',
    icon: EyeOff,
    title: 'No predictions.',
    body: 'No bail predictions, no scores for accused persons and no judge analytics. The court decides; Manu shows the record.',
  },
] as const;

const QUESTIONS = [
  {
    question: 'Does Manu file anything, or message anyone?',
    answer:
      'No. Manu prepares and people act. The morning cause list and client updates are drafts you copy or open in WhatsApp yourself; applications download as .docx for you to file. Tools that file, pay or contact anyone do not exist in Manu, and it refuses to register them.',
  },
  {
    question: 'How do I know a direction is really in the order?',
    answer:
      'Every direction carries the exact words it was read from. Click its number and the order opens at those words, highlighted, with whether they were found. Manu reads; a person confirms, completes or dismisses each direction.',
  },
  {
    question: 'Will it tell me whether bail will be granted?',
    answer:
      'No, and it never will. The liberty view shows the labels, the Section 479 and default-bail working and the six bail facts, each with a source or a gap. It never recommends an outcome, and there are no scores for accused persons and no judge analytics.',
  },
  {
    question: 'Which courts does it read?',
    answer:
      'Manu follows a case by its CNR, the number every eCourts case carries, in district courts and High Courts. Connectors go in a fixed order: an official API, then official public data, then a browser agent, and when none of those can reach a court, a person. Never a guess.',
  },
  {
    question: 'Where does the legal arithmetic come from?',
    answer:
      'From fixed rules written as code: Section 479 BNSS, default bail under Section 187(3) BNSS, and the last day for an appeal, revision, review, SLP or written statement. IPC or BNS is picked by the date of the offence, and the working is always one click away.',
  },
  {
    question: 'Is it only for advocates?',
    answer:
      'Advocates and their chambers come first. A firm uses the same diary across its matters, and a judge sees the same case page from the bench, with the cause list labelled. One record and one view: nobody switches modes.',
  },
] as const;

export function MarketingPage() {
  useHashScroll();

  return (
    <div className="marketing-page" id="top">
      <SiteHeader />
      <main>
        <section className="hero">
          <img
            className="hero__painting hero__painting--world"
            src="/art/manu-court-garden.webp"
            srcSet="/art/manu-court-garden-960.webp 960w, /art/manu-court-garden.webp 1672w"
            sizes="100vw"
            alt="Advocates in black gowns talking over case files under a banyan tree, with the Supreme Court of India in the distance, in ink and watercolour"
            width="1672"
            height="941"
            fetchPriority="high"
          />
          <div className="hero__wash" />
          <div className="hero__content">
            <Eyebrow>The case diary for Indian courts</Eyebrow>
            <h1>
              The case diary <em>that reads the court for you.</em>
            </h1>
            <p>
              Add a case by its CNR. Every morning Manu reads the court, notices what changed, reads each new order,
              and tells you what you have to do and by when, with the words it came from.
            </p>
            <div className="hero__actions">
              <ButtonLink href={APP_URL} tone="ink" arrow={false}>
                {APP_CTA_FIRST}
              </ButtonLink>
              <ButtonLink href="/#how-it-works" tone="outline" arrow>
                See how it works
              </ButtonLink>
            </div>
          </div>
        </section>

        <section className="product-section" id="product">
          <DiaryPreview />
        </section>

        <section className="system-section" id="how-it-works">
          {/* Tura's painted grid: the three steps as panels, and pointing at
            * one widens its columns and opens its preview. `system-card--1/2/3`
            * and `tabIndex` are load-bearing, as they are there. */}
          <img
            className="system-section__painting"
            src="/art/paper/paper-grove.webp"
            alt=""
            aria-hidden="true"
            width="1518"
            height="584"
            loading="lazy"
            decoding="async"
          />
          <div className="system-section__wash" aria-hidden="true" />
          <div className="system-section__grid">
            <header className="system-section__intro">
              <Eyebrow>How it works</Eyebrow>
              <h2>Three steps. Then the diary keeps itself.</h2>
              <p>
                Following a case takes its CNR. After that it is one screen: what is listed today, and what needs
                you.
              </p>
            </header>

            <article className="system-card system-card--1" tabIndex={0}>
              <span className="system-card__step">01</span>
              <h3>Follow a case.</h3>
              <p>
                Paste its CNR, or type an advocate&rsquo;s name and follow every case found in one go. That is the
                whole setup.
              </p>
              <div className="system-card__reveal">
                <div className="step-card__ui-mock">
                  <div className="step-card__ui-header">
                    <span>Following</span>
                    <Hash size={13} />
                  </div>
                  <div className="step-card__file-item">
                    <strong>
                      <Hash size={14} className="step-card__ico--blue" /> DLSE010007892026
                    </strong>
                    <span className="step-card__status-pill">Following</span>
                  </div>
                  <div className="step-card__file-item">
                    <strong>
                      <UserSearch size={14} className="step-card__ico--terracotta" /> Advocate &ldquo;R. Mehta&rdquo;
                    </strong>
                    <span className="step-card__status-pill step-card__status-pill--paper">2 found</span>
                  </div>
                </div>
              </div>
            </article>

            <article className="system-card system-card--2" tabIndex={0}>
              <span className="system-card__step">02</span>
              <h3>Manu reads the court.</h3>
              <p>
                Every morning it checks each case for a moved date, a new order, or a changed stage or status. Each
                change becomes an event with its source.
              </p>
              <div className="system-card__reveal">
                <div className="step-card__ui-mock">
                  <div className="step-card__ui-header">
                    <span>This morning</span>
                    <BellRing size={13} />
                  </div>
                  <div className="step-card__stat-callout">
                    <strong>Next date moved 25 Sep → 2 Oct</strong>
                    <span>State v. Aamir Khan · arguments on bail</span>
                  </div>
                  <div className="step-card__gap-pill">
                    <FileSearch size={12} />
                    <span>New order, 24 Sep: 2 directions found, with their words</span>
                  </div>
                </div>
              </div>
            </article>

            <article className="system-card system-card--3" tabIndex={0}>
              <span className="system-card__step">03</span>
              <h3>Do what the order says.</h3>
              <p>
                Every direction comes out of the order with its exact words: who, what, and by when. Confirm it and it
                goes on the diary.
              </p>
              <div className="system-card__reveal">
                <div className="step-card__ui-mock">
                  <div className="step-card__ui-header">
                    <span>To do</span>
                    <ListChecks size={13} />
                  </div>
                  <div className="step-card__path-list">
                    <div className="step-card__path-node is-active">
                      <strong>IO: reply with involvement report</strong>
                      <span className="step-card__marks-tag step-card__marks-tag--gap">30 Sep</span>
                    </div>
                    <div className="step-card__path-node">
                      <strong>IO: status report on investigation</strong>
                      <span className="step-card__marks-tag">Today</span>
                    </div>
                    <div className="step-card__path-node">
                      <strong className="is-quiet">Defendant: written statement</strong>
                      <span className="step-card__marks-tag is-quiet">28 Sep</span>
                    </div>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </section>

        <ProductTour />

        <section className="paper-section paper-section--sources" id="sources">
          <PaperGround tile="dome" />
          <div className="paper-section__inner">
            <div className="paper-section__copy">
              <Eyebrow>Every line cites its words</Eyebrow>
              <p className="paper-section__statement">
                A diary you have to check again is a second job. So every fact in Manu carries its source: the order,
                the page and the <mark>exact words</mark>, and whether they were really found there.
              </p>
              <figure className="change-card">
                <figcaption>Something changed this morning</figcaption>
                <p>
                  <strong>State v. Aamir Khan</strong>: next date moved 25 Sep → 2 Oct, arguments on the bail
                  application.
                </p>
                <p>
                  New order, 24 Sep: the IO is directed to file the reply along with the previous involvement report on
                  or before 30.09.2026, failing which the SHO concerned shall remain present in person.
                  <sup>1</sup>
                </p>
                <footer>
                  <span>
                    <b>1</b> Order dated 24.09.2026 · words found
                  </span>
                  <span className="change-card__actions">
                    <i>
                      <Check size={13} strokeWidth={2.4} aria-hidden="true" /> Confirm
                    </i>
                    <i>Done</i>
                  </span>
                </footer>
              </figure>
            </div>
          </div>
        </section>

        <section className="paper-section paper-section--liberty" id="liberty">
          <PaperGround tile="scales" />
          <div className="paper-section__inner">
            <div className="paper-section__copy">
              <Eyebrow>Liberty, for everyone</Eyebrow>
              <h2>
                The custody arithmetic, with its working.
                <em>The decision stays with the court.</em>
              </h2>
              <p>
                For criminal matters Manu works out Section 479 BNSS and default-bail status from the record, and lists
                the six bail facts, each with a source or a gap. The advocate and the judge read the same page, and it
                never recommends an outcome.
              </p>
              <dl className="liberty-labels">
                {LIBERTY_LABELS.map(([code, meaning]) => (
                  <div key={code} className={`liberty-labels__row is-${code.toLowerCase().replace(/\s+/g, '-')}`}>
                    <dt>{code}</dt>
                    <dd>{meaning}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </section>

        <section className="about-precepts" id="principles">
          <header className="about-precepts__head">
            <Eyebrow>What Manu will not do</Eyebrow>
            <h2>
              Manu prepares. <em>People act.</em>
            </h2>
          </header>
          <div className="about-precepts__grid">
            {PRINCIPLES.map((principle) => {
              const Icon = principle.icon;
              return (
                <article key={principle.title} className={`about-precept tone-${principle.tone}`}>
                  <div className="about-precept__band">
                    <span className="about-precept__icon">
                      <Icon size={24} strokeWidth={1.7} aria-hidden="true" />
                    </span>
                  </div>
                  <div className="about-precept__body">
                    <h3>{principle.title}</h3>
                    <p>{principle.body}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="faq-band" id="questions">
          <PaperGround tile="circuit" />
          <div className="faq-section">
            <header className="faq-section__heading">
              <Eyebrow>Questions</Eyebrow>
              <h2>Everything you need to know.</h2>
            </header>
            <div className="faq-section__list">
              {QUESTIONS.map((item) => (
                <details key={item.question}>
                  <summary>
                    {item.question} <i>+</i>
                  </summary>
                  <p>{item.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="closing-section">
          <PaperThreads tone="navy" seed={24} strands={8} pins={3} ring band={[0.34, 0.92]} className="closing-section__threads" />
          <div>
            <Eyebrow inverse>Start with one case</Eyebrow>
            <h2>
              Your CNR,
              <br />
              and about a minute.
            </h2>
            <p className="closing-section__proof">
              <span><CalendarClock size={15} aria-hidden="true" /> Tomorrow morning, the diary is already read.</span>
              <span><CheckCircle2 size={15} aria-hidden="true" /> Every line with its source.</span>
            </p>
            <ButtonLink href={APP_URL} tone="paper">
              {APP_CTA}
            </ButtonLink>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

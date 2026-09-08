import {
  ArrowRight,
  BadgeCheck,
  Blocks,
  BoxSelect,
  Braces,
  FileSearch,
  Files,
  GitCompareArrows,
  HelpCircle,
  MapPin,
  MessageSquareText,
  RefreshCw,
  Scale,
  ScanLine,
  ShieldCheck,
  SlidersHorizontal,
  Unlink,
  Upload,
} from "lucide-react";
import { Link } from "react-router-dom";

const processSteps = [
  { title: "Upload", description: "Add arbitrary PDFs through the interface.", icon: Upload },
  { title: "Evidence", description: "PyMuPDF extracts page and block evidence with provenance.", icon: ScanLine },
  { title: "Facts", description: "Structured numerical and semantic facts are extracted.", icon: Braces },
  { title: "Normalize", description: "Units, dates, percentages, fiscal periods, and entities are aligned.", icon: Scale },
  { title: "Compare", description: "Comparable facts across documents are matched.", icon: GitCompareArrows },
  { title: "Explain", description: "Relationships are labeled and explained using evidence and context.", icon: MessageSquareText },
];

const relationshipTypes = [
  { type: "CORROBORATES", description: "Two facts agree after normalization and context checks.", icon: BadgeCheck },
  { type: "CONTRADICTS", description: "Comparable facts report materially conflicting values.", icon: GitCompareArrows },
  { type: "RECONCILABLE", description: "Context such as unit, time, scope, or data vintage explains an apparent disagreement.", icon: RefreshCw },
  { type: "NEEDS REVIEW", description: "There is not enough reliable context to classify safely.", icon: HelpCircle },
  { type: "UNRELATED", description: "The facts are not truly comparable.", icon: Unlink },
];

const features = [
  { title: "Arbitrary PDF ingestion", description: "Bring source documents into one inspectable workspace.", icon: Files },
  { title: "Evidence-level provenance", description: "Trace facts to their exact page and evidence block.", icon: MapPin },
  { title: "Structured fact extraction", description: "Turn prose and tables into validated fact records.", icon: BoxSelect },
  { title: "Deterministic normalization", description: "Align values, units, entities, and reporting periods.", icon: SlidersHorizontal },
  { title: "Cross-document comparison", description: "Find agreements and meaningful differences across sources.", icon: GitCompareArrows },
  { title: "Explainable review workflow", description: "Inspect context and resolve uncertainty without guessing.", icon: ShieldCheck },
];

export function HomePage() {
  return <div className="home-page">
    <a className="skip-link" href="#home-main">Skip to content</a>
    <header className="home-nav">
      <Link className="home-brand" to="/" aria-label="Fact-O-Check home">
        <span aria-hidden="true">F</span>
        <strong>Fact-O-Check</strong>
      </Link>
      <nav aria-label="Home navigation">
        <a href="#how-it-works">How it works</a>
        <a href="#evidence">Evidence</a>
        <Link to="/documents">Documents</Link>
      </nav>
      <Link className="button button--primary home-nav__cta" to="/overview">
        Open Workspace <ArrowRight size={15} aria-hidden="true" />
      </Link>
    </header>

    <main id="home-main">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-hero__copy">
          <span className="home-kicker"><BadgeCheck size={14} aria-hidden="true" /> Facts, grounded in evidence.</span>
          <h1 id="home-title">Turn PDFs into <em>evidence-backed facts.</em></h1>
          <p>Fact-O-Check extracts structured facts from PDFs, links every fact to source evidence, normalizes values and context, and compares claims across documents.</p>
          <div className="home-actions">
            <Link className="button button--primary home-button" to="/overview">Open Workspace <ArrowRight size={16} /></Link>
            <Link className="button button--secondary home-button" to="/documents">View Documents</Link>
          </div>
          <div className="home-hero__trust" aria-label="Product principles">
            <span><ShieldCheck size={14} /> Validated structure</span>
            <span><MapPin size={14} /> Source provenance</span>
            <span><Scale size={14} /> Context-aware comparison</span>
          </div>
        </div>
        <div className="home-hero__visual" aria-label="Illustration of the evidence-to-fact workflow">
          <span className="illustrative-label">Illustrative workflow</span>
          <div className="source-sheet">
            <div className="source-sheet__top"><FileSearch size={17} /><span>Source PDF</span><small>Page</small></div>
            <div className="source-lines"><i /><i /><i /><i /></div>
            <div className="source-highlight"><ScanLine size={15} /><span>Evidence block retained</span></div>
          </div>
          <div className="structured-fact-card">
            <div><span>Structured fact</span><BadgeCheck size={16} /></div>
            <dl>
              <div><dt>Subject</dt><dd>Example entity</dd></div>
              <div><dt>Predicate</dt><dd>Example metric</dd></div>
              <div><dt>Value</dt><dd>123.4</dd></div>
            </dl>
            <span className="evidence-linked"><MapPin size={13} /> Evidence linked</span>
          </div>
        </div>
      </section>

      <section className="home-section home-problem" aria-labelledby="why-title">
        <div className="home-section__intro">
          <span className="eyebrow">Why Fact-O-Check</span>
          <h2 id="why-title">PDF search can find text.<br /><em>Fact-O-Check finds claims.</em></h2>
        </div>
        <div className="problem-comparison">
          <article><span>Traditional retrieval</span><h3>Here is a relevant passage.</h3><p>Useful for discovery, but the user still has to interpret the value, period, scope, and source.</p></article>
          <ArrowRight className="problem-arrow" aria-hidden="true" />
          <article className="problem-comparison__solution"><span>Structured knowledge</span><h3>Here is the claim—and its receipts.</h3><p>A typed fact with normalized context and a direct path back to the source evidence.</p></article>
        </div>
      </section>

      <section className="home-section" id="how-it-works" aria-labelledby="process-title">
        <div className="home-section__intro home-section__intro--center">
          <span className="eyebrow">From document to decision</span>
          <h2 id="process-title">How the full pipeline works</h2>
          <p>Each stage adds structure while preserving the evidence needed to inspect the result.</p>
        </div>
        <ol className="home-process">
          {processSteps.map(({ title, description, icon: Icon }, index) => <li key={title}>
            <div className="home-process__top"><span>{String(index + 1).padStart(2, "0")}</span><Icon size={18} /></div>
            <h3>{title}</h3><p>{description}</p>
          </li>)}
        </ol>
      </section>

      <section className="home-section" aria-labelledby="relationships-title">
        <div className="home-section__intro">
          <span className="eyebrow">Explainable relationships</span>
          <h2 id="relationships-title">What can Fact-O-Check discover?</h2>
          <p>Labels describe what the available evidence supports—not what the system hopes to find.</p>
        </div>
        <div className="home-relations">
          {relationshipTypes.map(({ type, description, icon: Icon }) => <article className={`home-relation home-relation--${type.toLowerCase().replace(" ", "-")}`} key={type}>
            <Icon size={18} aria-hidden="true" /><h3>{type}</h3><p>{description}</p>
          </article>)}
        </div>
      </section>

      <section className="home-section evidence-first" id="evidence" aria-labelledby="evidence-title">
        <div className="evidence-first__copy">
          <span className="eyebrow">Evidence first</span>
          <h2 id="evidence-title">Every fact has receipts.</h2>
          <p>Every extracted fact stays connected to the material that supports it. Inspect the source PDF, page number, evidence block, spatial context, raw value, and normalized value from one place.</p>
          <ul>
            <li><FileSearch size={16} /> Source PDF and page</li>
            <li><Blocks size={16} /> Evidence block and bounding box</li>
            <li><Braces size={16} /> Raw and normalized values</li>
          </ul>
        </div>
        <article className="evidence-demo">
          <span className="illustrative-label">Illustrative UI · not persisted data</span>
          <header><div><small>Fact</small><h3>Example metric</h3></div><span className="confidence confidence--high">Grounded</span></header>
          <dl>
            <div><dt>Raw value</dt><dd>123.4</dd></div>
            <div><dt>Normalized value</dt><dd>123.4</dd></div>
            <div><dt>Source</dt><dd>Source PDF</dd></div>
            <div><dt>Page</dt><dd>—</dd></div>
          </dl>
          <div className="evidence-demo__snippet"><span>Evidence</span><p>Highlighted source evidence appears here for direct inspection.</p></div>
        </article>
      </section>

      <section className="home-section reasoning-first" aria-labelledby="reasoning-title">
        <div>
          <span className="eyebrow">Deterministic-first reasoning</span>
          <h2 id="reasoning-title">Rules first. AI only when needed.</h2>
          <blockquote>“Deterministic checks decide clear numerical relationships; LLM reasoning is reserved for ambiguous semantic context.”</blockquote>
          <p>Unclear cases become <strong>NEEDS REVIEW</strong> instead of being guessed.</p>
        </div>
        <ul>
          {[
            "Unit normalization", "Percentage comparison", "Fiscal-period matching",
            "Typed tolerances", "Scope and geography checks", "Semantic fallback",
          ].map((item, index) => <li key={item}><span>{index < 5 ? "Rule" : "Fallback"}</span>{item}</li>)}
        </ul>
      </section>

      <section className="home-section proof-section" aria-labelledby="proof-title">
        <div className="home-section__intro home-section__intro--center">
          <span className="eyebrow">Tested beyond toy examples</span>
          <h2 id="proof-title">Validated on real documents</h2>
          <p>Project validation records what the evidence demonstrated—including when it did not support a label.</p>
        </div>
        <div className="proof-list">
          <span><BadgeCheck size={16} /> Corroboration across India macroeconomic sources</span>
          <span><RefreshCw size={16} /> Reconciliation using data-vintage context</span>
          <span><FileSearch size={16} /> A real PDF layout failure documented</span>
          <span><ShieldCheck size={16} /> No contradiction forced without evidence</span>
        </div>
        <Link to="/relationships">Explore Relationships <ArrowRight size={15} /></Link>
      </section>

      <section className="home-section" aria-labelledby="features-title">
        <div className="home-section__intro">
          <span className="eyebrow">The workspace</span>
          <h2 id="features-title">Built for inspection, not blind trust.</h2>
        </div>
        <div className="home-features">
          {features.map(({ title, description, icon: Icon }) => <article key={title}>
            <Icon size={18} /><h3>{title}</h3><p>{description}</p>
          </article>)}
        </div>
      </section>

      <section className="home-cta" aria-labelledby="cta-title">
        <span className="eyebrow">Start with a source</span>
        <h2 id="cta-title">Ready to inspect your documents?</h2>
        <p>Upload a PDF, extract grounded facts, and see where your sources agree.</p>
        <div className="home-actions">
          <Link className="button button--primary home-button" to="/documents">Upload a Document <ArrowRight size={16} /></Link>
          <Link className="button button--secondary home-button" to="/relationships">Open Relationships</Link>
        </div>
      </section>
    </main>

    <footer className="home-footer">
      <div><strong>Fact-O-Check</strong><p>Facts, not text chunks, are the primary unit of knowledge.</p></div>
      <nav aria-label="Footer navigation">
        <Link to="/">Home</Link><Link to="/documents">Documents</Link><Link to="/facts">Facts</Link><Link to="/relationships">Relationships</Link>
      </nav>
    </footer>
  </div>;
}

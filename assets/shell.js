/* Grow10x — shared site shell.
   Injects nav + footer into placeholders, manages color-emphasis tweak,
   persists choice across page navigation via localStorage,
   and speaks the Tweaks-panel protocol with the host.

   Usage: include with <script src="..."> AFTER the placeholder elements
   <header id="site-nav"></header> and <footer id="site-foot"></footer>.
   Optional: <body data-page="solutions"> to flag current top-level. */

(function () {
  const LOGO = withBase("assets/logo-grow10x.png");

  function withBase(p) {
    // resolves relative to the document, walking up one level per "../"
    const depth = (document.body && document.body.dataset && document.body.dataset.depth) || "0";
    const up = "../".repeat(Number(depth));
    return up + p;
  }

  const NAV = [
    { href: "home",       label: "Home",       key: "home" },
    { href: "solutions",  label: "Solutions",  key: "solutions" },
    { href: "industries", label: "Industries", key: "industries" },
    { href: "resources",  label: "Resources",  key: "resources" },
    { href: "about",      label: "About Us",   key: "about" },
    { href: "clients",    label: "Clients",    key: "clients" },
  ];

  const HUBS = {
    home:       { url: "/" },
    solutions:  { url: "/solutions" },
    industries: { url: "/industries" },
    resources:  { url: "/resources" },
    about:      { url: "/about" },
    clients:    { url: "/clients" },
  };

  // ------- color emphasis (the tweak) -------
  const EMP_KEY = "gtxo_emphasis";
  function getEmphasis() {
    try {
      const stored = localStorage.getItem(EMP_KEY);
      if (stored) return stored;
    } catch (e) {}
    // fall back to the EDITMODE-BEGIN block on the home page
    if (window.__TWEAKS && window.__TWEAKS.emphasis) return window.__TWEAKS.emphasis;
    return "blue";
  }
  function setEmphasis(value, persistToHost) {
    try { localStorage.setItem(EMP_KEY, value); } catch (e) {}
    document.body.setAttribute("data-emphasis", value);
    document.querySelectorAll(".tweaks-panel .swatch").forEach(b => {
      b.setAttribute("aria-pressed", b.dataset.value === value ? "true" : "false");
    });
    if (persistToHost) {
      try {
        window.parent.postMessage({ type: "__edit_mode_set_keys", edits: { emphasis: value } }, "*");
      } catch (e) {}
    }
  }

  // ------- nav -------
  function renderNav() {
    const host = document.getElementById("site-nav");
    if (!host) return;
    const current = document.body.dataset.page || "";
    const base = withBase("");
    const links = NAV.map(item => {
      const url = HUBS[item.key].url;
      const isCurrent = current === item.key;
      return `<a href="${url}"${isCurrent ? ' data-current="true"' : ""}>${item.label}</a>`;
    }).join("");

    const __banner = /*BANNER-BEGIN*/``/*BANNER-END*/;
    host.innerHTML = `
      ${__banner}
      <nav class="nav" aria-label="Primary">
        <div class="container nav-inner">
          <a class="brand" href="/">
            <img src="${LOGO}" alt="Grow10x" style="height:34px;width:auto;" />
          </a>
          <div class="nav-links">${links}</div>
          <div class="nav-actions">
            <a class="btn btn-cube btn-sm" href="/contact">Book a consultation <span class="arr">→</span></a>
          </div>
        </div>
      </nav>
    `;
  }

  // ------- footer -------
  function renderFooter() {
    const host = document.getElementById("site-foot");
    if (!host) return;
    const base = withBase("");
    host.innerHTML = `
      <footer class="foot">
        <div class="container">
          <div class="foot-grid">
            <div>
              <div class="foot-brand">
                <img src="${withBase("assets/logo-grow10x-white.png")}" alt="GTXO Consulting" style="height:36px;width:auto;" />
              </div>
              <p class="tag">Your extended marketing team focused on one objective: revenue growth.</p>
            </div>
            <div>
              <h4>Solutions</h4>
              <ul>
                <li><a href="/solutions/paid-marketing">Paid Marketing</a></li>
                <li><a href="/solutions/ai-led-seo">AI-Led SEO</a></li>
                <li><a href="/solutions/content-strategy">Content Strategy</a></li>
                <li><a href="/solutions/gtm-strategy">GTM Strategy</a></li>
                <li><a href="/solutions/demand-gen">Demand Gen</a></li>
                <li><a href="/solutions/ai-solutions">AI Solutions</a></li>
              </ul>
            </div>
            <div>
              <h4>Industries</h4>
              <ul>
                <li><a href="/industries/b2b-tech">B2B Tech</a></li>
                <li><a href="/industries/b2b-consulting">B2B Consulting</a></li>
                <li><a href="/industries/d2c-brands">D2C Brands</a></li>
                <li><a href="/industries/b2c-brands">B2C Brands</a></li>
              </ul>
            </div>
            <div>
              <h4>Resources</h4>
              <ul>
                <li><a href="/resources/blogs">Blogs</a></li>
                <li><a href="/resources/case-studies">Case Studies</a></li>
                <li><a href="/resources/guides">Guides</a></li>
              </ul>
            </div>
            <div>
              <h4>Company</h4>
              <ul>
                <li><a href="/about">About Us</a></li>
                <li><a href="/clients">Clients</a></li>
                <li><a href="/contact">Contact</a></li>
              </ul>
            </div>
          </div>
          <div class="copy" style="justify-content:center;text-align:center;">
            <span>© GTXO Consulting 2026, Your Embedded Growth Partner</span>
          </div>
        </div>
      </footer>
    `;
  }

  // ------- tweaks panel -------
  function renderTweaks() {
    if (document.querySelector(".tweaks-panel")) return;
    const el = document.createElement("div");
    el.className = "tweaks-panel";
    el.setAttribute("aria-label", "Tweaks");
    el.innerHTML = `
      <div class="head">
        <span class="ttl">Tweaks</span>
        <button class="close" aria-label="Close">×</button>
      </div>
      <div class="lbl">Color emphasis</div>
      <div class="swatches">
        <button class="swatch" data-value="blue" aria-pressed="false">
          <span class="chip blue"></span><span class="name">Blue</span>
        </button>
        <button class="swatch" data-value="cyber" aria-pressed="false">
          <span class="chip cyber"></span><span class="name">Cyber</span>
        </button>
        <button class="swatch" data-value="energy" aria-pressed="false">
          <span class="chip energy"></span><span class="name">Energy</span>
        </button>
      </div>
    `;
    document.body.appendChild(el);

    el.querySelectorAll(".swatch").forEach(b => {
      b.addEventListener("click", () => setEmphasis(b.dataset.value, true));
    });
    el.querySelector(".close").addEventListener("click", () => {
      el.classList.remove("open");
      try { window.parent.postMessage({ type: "__edit_mode_dismissed" }, "*"); } catch (e) {}
    });
  }

  function openTweaks() {
    const el = document.querySelector(".tweaks-panel");
    if (el) el.classList.add("open");
  }
  function closeTweaks() {
    const el = document.querySelector(".tweaks-panel");
    if (el) el.classList.remove("open");
  }

  // ------- protocol -------
  window.addEventListener("message", (ev) => {
    const d = ev && ev.data;
    if (!d || typeof d !== "object") return;
    if (d.type === "__activate_edit_mode") openTweaks();
    if (d.type === "__deactivate_edit_mode") closeTweaks();
  });

  // ------- boot -------
  function injectFavicon() {
    if (document.querySelector('link[rel="icon"]')) return;
    const link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/png";
    link.href = withBase("assets/favicon.png");
    document.head.appendChild(link);
    const apple = document.createElement("link");
    apple.rel = "apple-touch-icon";
    apple.href = withBase("assets/favicon.png");
    document.head.appendChild(apple);
  }

  function boot() {
    // apply emphasis BEFORE rendering so first paint is correct
    document.body.setAttribute("data-emphasis", getEmphasis());

    injectFavicon();
    renderNav();
    renderFooter();
    renderTweaks();
    // sync swatches to current value (no host post — just a state sync)
    setEmphasis(getEmphasis(), false);

    try {
      window.parent.postMessage({ type: "__edit_mode_available" }, "*");
    } catch (e) {}
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

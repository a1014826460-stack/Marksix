import fs from "node:fs"
import { Script, createContext } from "node:vm"

// ---------------------------------------------------------------------------
// Verify the shared script file exists
// ---------------------------------------------------------------------------
const scriptPath = "frontend/public/vendor/_shared/managed-site-links.js"
let scriptSource
try {
  scriptSource = fs.readFileSync(scriptPath, "utf8")
} catch (_) {
  throw new Error(`managed-site-links.js not found at ${scriptPath}`)
}

// ---------------------------------------------------------------------------
// Static source-level assertions (before runtime)
// ---------------------------------------------------------------------------

// Must not contain any hardcoded supplier domains
const forbiddenDomainTokens = [
  "tw8800.com", "twcf888.com", "twtongtian.com", "twsaimahui.com",
  "twssz.com", "www.twbst528.com", "twjsz666.example.com",
  "shengshi8800", "twcf888", "twjinniu", "twbst528",
]
for (const token of forbiddenDomainTokens) {
  if (scriptSource.includes(token)) {
    throw new Error(`component must not contain hardcoded supplier domain: ${token}`)
  }
}

// Must use customElements.define
if (!scriptSource.includes("customElements.define")) {
  throw new Error("component must register via customElements.define")
}

// Must reference the API endpoint
if (!scriptSource.includes("/api/site-links")) {
  throw new Error("component must fetch from /api/site-links")
}

// Must include target=_blank
if (!scriptSource.includes("target") || !scriptSource.includes("_blank")) {
  throw new Error("component must use target=_blank on links")
}

// Must include rel=noopener
if (!scriptSource.includes("rel") || !scriptSource.includes("noopener")) {
  throw new Error("component must use rel=noopener on links")
}

// ---------------------------------------------------------------------------
// Build mock DOM / VM environment with per-sandbox tracking
// ---------------------------------------------------------------------------

// Shared fetch state (tests reset between runs)
let fetchCalls = []
let fetchResponse = null
let fetchShouldFail = false

function resetFetchState(response, shouldFail) {
  fetchCalls = []
  fetchResponse = response
  fetchShouldFail = !!shouldFail
}

function mockFetch(url) {
  fetchCalls.push({ url, index: fetchCalls.length })
  if (fetchShouldFail) return Promise.reject(new Error("Network error"))
  return Promise.resolve({
    ok: fetchResponse ? true : false,
    status: fetchResponse ? 200 : 500,
    json: () => Promise.resolve(fetchResponse || { links: [] }),
  })
}

// Mock ShadowRoot internal node
function createMockContainer() {
  const container = {
    __children: [],
    __innerHTML: "",
    get innerHTML() { return this.__innerHTML },
    set innerHTML(v) { this.__innerHTML = v; this.__children = [] },
    appendChild(el) { this.__children.push(el) },
    replaceChildren(...els) { this.__children = els },
  }
  return container
}

// Mock ShadowRoot
function createMockShadowRoot() {
  const linksContainer = createMockContainer()
  const titleElement = { textContent: "" }

  const root = {
    __innerHTML: "",
    __linksContainer: linksContainer,
    __titleElement: titleElement,

    get innerHTML() { return this.__innerHTML },
    set innerHTML(v) {
      this.__innerHTML = v
      // Parse [data-title] text from the template for querySelector to return
      var titleMatch = v.match(/<div[^>]*data-title[^>]*>([^<]*)<\/div>/)
      if (titleMatch) titleElement.textContent = titleMatch[1]
    },

    querySelector(selector) {
      if (selector === '[data-links]' || selector === '[data-links-container]') return linksContainer
      if (selector === '[data-title]') return titleElement
      if (selector === '[data-section]') return { __linksContainer: linksContainer, __titleElement: titleElement }
      return null
    },
  }
  return root
}

// Mock document — each sandbox gets its own anchor tracking array
function createMockDocument(anchorTracker) {
  return {
    createElement(tag) {
      const el = {
        _tag: tag,
        href: "",
        target: "",
        rel: "",
        textContent: "",
      }
      el.setAttribute = function (name, value) {
        this[name] = value
      }
      el.getAttribute = function (name) {
        return this[name] != null ? String(this[name]) : null
      }
      if (anchorTracker) anchorTracker.push(el)
      return el
    },
  }
}

// Mock customElements registry
const customElementsRegistry = {}

// Build the sandbox — returns sandbox object plus tracking arrays
function buildSandbox() {
  const anchorTracker = []
  const instanceTracker = []

  function MockHTMLElement() {
    this._attrs = {}
    this._shadowRoot = null
    this._connected = false
    instanceTracker.push(this)
  }

  MockHTMLElement.prototype.getAttribute = function (name) {
    return this._attrs[name] != null ? this._attrs[name] : null
  }

  MockHTMLElement.prototype.setAttribute = function (name, value) {
    this._attrs[name] = String(value)
  }

  MockHTMLElement.prototype.hasAttribute = function (name) {
    return this._attrs[name] !== undefined
  }

  MockHTMLElement.prototype.removeAttribute = function (name) {
    delete this._attrs[name]
  }

  MockHTMLElement.prototype.attachShadow = function () {
    this._attachShadowCalls = (this._attachShadowCalls || 0) + 1
    this._shadowRoot = createMockShadowRoot()
    return this._shadowRoot
  }

  Object.defineProperty(MockHTMLElement.prototype, "shadowRoot", {
    get: function () { return this._shadowRoot },
    configurable: true,
  })

  MockHTMLElement.prototype.connectedCallback = function () {}
  MockHTMLElement.prototype.disconnectedCallback = function () {}
  MockHTMLElement.prototype.attributeChangedCallback = function () {}

  const sandbox = {
    window: undefined,
    document: createMockDocument(anchorTracker),
    customElements: {
      define(name, constructor) {
        customElementsRegistry[name] = constructor
      },
      get(name) {
        return customElementsRegistry[name] || undefined
      },
    },
    HTMLElement: MockHTMLElement,
    fetch: mockFetch,
    encodeURIComponent: encodeURIComponent,
    Reflect: Reflect,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    Promise: Promise,
    Error: Error,
    JSON: JSON,
    Object: Object,
    Array: Array,
    String: String,
    Number: Number,
    Boolean: Boolean,
    Date: Date,
    isNaN: isNaN,
    parseInt: parseInt,
    parseFloat: parseFloat,
    undefined: undefined,
    null: null,
    console: {
      log() {},
      warn() {},
      error() {},
    },
    // Per-sandbox tracking (tests access these)
    _anchorTracker: anchorTracker,
    _instanceTracker: instanceTracker,
  }

  sandbox.window = sandbox
  return sandbox
}

// ---------------------------------------------------------------------------
// Helper: create a managed-site-links element and trigger connect
// ---------------------------------------------------------------------------
function createElement(siteKey) {
  const sandbox = buildSandbox()
  const context = createContext(sandbox)

  // Execute component script in sandbox
  const script = new Script(scriptSource)
  script.runInContext(context)

  const Ctor = customElementsRegistry["managed-site-links"]
  if (!Ctor) {
    throw new Error("Component did not register managed-site-links custom element")
  }

  // Create instance inside the sandbox
  const createFn = new Script(`
    (function(siteKey) {
      const el = new (customElements.get('managed-site-links'))();
      if (siteKey !== undefined) el.setAttribute('site-key', siteKey);
      return el;
    })
  `)
  const el = createFn.runInContext(context)(siteKey)

  // Trigger connectedCallback
  if (typeof el.connectedCallback === "function") {
    el.connectedCallback()
  }

  return { el, context, sandbox }
}

// ---------------------------------------------------------------------------
// Test 1 — Missing site-key attribute: still renders, no fetch
// ---------------------------------------------------------------------------
{
  resetFetchState(null, false)

  const { el, sandbox } = createElement(undefined)

  // No fetch should be triggered when site-key is missing
  if (fetchCalls.length !== 0) {
    throw new Error(`missing site-key triggered ${fetchCalls.length} fetch calls, expected 0`)
  }

  // Element should have shadow root
  if (!el.shadowRoot) {
    throw new Error("missing site-key: element must still create shadow root")
  }

  console.log("Test 1 passed: missing site-key attribute triggers no fetch")
}

// ---------------------------------------------------------------------------
// Test 2 — Valid site-key: single fetch to correct endpoint
// ---------------------------------------------------------------------------
{
  const linksPayload = {
    links: [
      { site_key: "shengshi8800", name: "盛世台湾六合彩", domain: "www.tw8800.com", url: "https://www.tw8800.com/" },
    ],
  }
  resetFetchState(linksPayload, false)

  const { el } = createElement("twjsz666")

  // Exactly one fetch
  if (fetchCalls.length !== 1) {
    throw new Error(`valid site-key triggered ${fetchCalls.length} fetch calls, expected 1`)
  }

  // Fetch URL must be same-origin /api/site-links?site_key=...
  const fetchUrl = fetchCalls[0].url
  if (!fetchUrl.startsWith("/api/site-links")) {
    throw new Error(`fetch URL ${fetchUrl} does not start with /api/site-links`)
  }
  if (!fetchUrl.includes("site_key=twjsz666")) {
    throw new Error(`fetch URL ${fetchUrl} missing site_key=twjsz666`)
  }

  // Shadow root must exist
  if (!el.shadowRoot) {
    throw new Error("valid site-key: element must create shadow root")
  }

  // Title should be preserved and non-empty
  const titleEl = el.shadowRoot.querySelector('[data-title]')
  if (!titleEl || !titleEl.textContent) {
    throw new Error("valid site-key: title must be preserved and non-empty")
  }

  console.log("Test 2 passed: valid site-key triggers single fetch to correct endpoint with title")
}

// ---------------------------------------------------------------------------
// Test 3 — Rendered links use HTTPS, target=_blank, rel=noopener noreferrer
// ---------------------------------------------------------------------------
{
  const linksPayload = {
    links: [
      { site_key: "site-a", name: "Alpha", domain: "alpha.example.com", url: "https://alpha.example.com/" },
      { site_key: "site-b", name: "Beta", domain: "beta.example.com", url: "https://beta.example.com/" },
    ],
  }
  resetFetchState(linksPayload, false)

  const { sandbox } = createElement("twjsz666")

  // Wait for async fetch to resolve
  await new Promise((resolve) => setTimeout(resolve, 50))

  const anchors = sandbox._anchorTracker
  if (anchors.length !== 2) {
    throw new Error(`expected 2 anchor elements, got ${anchors.length}`)
  }

  for (let i = 0; i < anchors.length; i++) {
    const a = anchors[i]
    const link = linksPayload.links[i]

    if (a.target !== "_blank") {
      throw new Error(`link ${i}: expected target=_blank, got target=${a.target}`)
    }
    if (a.rel !== "noopener noreferrer") {
      throw new Error(`link ${i}: expected rel=noopener noreferrer, got rel=${a.rel}`)
    }
    if (!a.href.startsWith("https://")) {
      throw new Error(`link ${i}: expected https:// URL, got href=${a.href}`)
    }
    if (a.href !== link.url) {
      throw new Error(`link ${i}: expected href=${link.url}, got href=${a.href}`)
    }
    if (a.textContent !== link.name) {
      throw new Error(`link ${i}: expected text=${link.name}, got text=${a.textContent}`)
    }
  }

  console.log("Test 3 passed: links have correct HTTPS URLs, target=_blank, rel=noopener noreferrer")
}

// ---------------------------------------------------------------------------
// Test 4 — Ordered rendering (backend order preserved)
// ---------------------------------------------------------------------------
{
  const linksPayload = {
    links: [
      { site_key: "third", name: "Third", domain: "third.example.com", url: "https://third.example.com/" },
      { site_key: "first", name: "First", domain: "first.example.com", url: "https://first.example.com/" },
      { site_key: "second", name: "Second", domain: "second.example.com", url: "https://second.example.com/" },
    ],
  }
  resetFetchState(linksPayload, false)

  const { sandbox } = createElement("twjsz666")
  await new Promise((resolve) => setTimeout(resolve, 50))

  const anchors = sandbox._anchorTracker
  if (anchors.length !== 3) {
    throw new Error(`expected 3 anchor elements, got ${anchors.length}`)
  }

  // Order must match backend order
  for (let i = 0; i < linksPayload.links.length; i++) {
    if (anchors[i].textContent !== linksPayload.links[i].name) {
      throw new Error(
        `order mismatch at index ${i}: expected "${linksPayload.links[i].name}", got "${anchors[i].textContent}"`
      )
    }
  }

  console.log("Test 4 passed: links rendered in backend order")
}

// ---------------------------------------------------------------------------
// Test 5 — Empty links array: title preserved, link area empty, no fallback
// ---------------------------------------------------------------------------
{
  resetFetchState({ links: [] }, false)

  const { el, sandbox } = createElement("twjsz666")
  await new Promise((resolve) => setTimeout(resolve, 50))

  // Title must be preserved
  const titleEl = el.shadowRoot.querySelector('[data-title]')
  if (!titleEl || !titleEl.textContent) {
    throw new Error("empty array: title must be preserved")
  }

  // No anchor elements created
  if (sandbox._anchorTracker.length !== 0) {
    throw new Error(`empty array: expected 0 anchor elements, got ${sandbox._anchorTracker.length}`)
  }

  // Links container must have no children
  const linksContainer = el.shadowRoot.querySelector('[data-links]')
  if (linksContainer.__children.length !== 0) {
    throw new Error("empty array: links container must have no children")
  }

  console.log("Test 5 passed: empty links array preserves title, clears link area, no fallback")
}

// ---------------------------------------------------------------------------
// Test 6 — Fetch error: title preserved, link area empty, no fallback
// ---------------------------------------------------------------------------
{
  resetFetchState(null, true)

  const { el, sandbox } = createElement("twjsz666")
  await new Promise((resolve) => setTimeout(resolve, 50))

  // Title must be preserved
  const titleEl = el.shadowRoot.querySelector('[data-title]')
  if (!titleEl || !titleEl.textContent) {
    throw new Error("fetch error: title must be preserved")
  }

  // No anchor elements created
  if (sandbox._anchorTracker.length !== 0) {
    throw new Error(`fetch error: expected 0 anchor elements, got ${sandbox._anchorTracker.length}`)
  }

  // Links container must be empty
  const linksContainer = el.shadowRoot.querySelector('[data-links]')
  if (linksContainer.__children.length !== 0) {
    throw new Error("fetch error: links container must have no children")
  }

  console.log("Test 6 passed: fetch error preserves title, clears link area, no fallback")
}

// ---------------------------------------------------------------------------
// Test 7 — Non-ok response: title preserved, link area empty
// ---------------------------------------------------------------------------
{
  // fetchResponse = null => ok: false (server error response)
  resetFetchState(null, false)

  const { el, sandbox } = createElement("twjsz666")
  await new Promise((resolve) => setTimeout(resolve, 50))

  const titleEl = el.shadowRoot.querySelector('[data-title]')
  if (!titleEl || !titleEl.textContent) {
    throw new Error("non-ok response: title must be preserved")
  }
  if (sandbox._anchorTracker.length !== 0) {
    throw new Error(`non-ok response: expected 0 anchor elements, got ${sandbox._anchorTracker.length}`)
  }

  console.log("Test 7 passed: non-ok response preserves title, clears link area")
}

// ---------------------------------------------------------------------------
// Test 8 — Each element instance fetches exactly once (one fetch per connection)
// ---------------------------------------------------------------------------
{
  const linksPayload = {
    links: [{ site_key: "site-x", name: "X", domain: "x.example.com", url: "https://x.example.com/" }],
  }
  resetFetchState(linksPayload, false)

  const sandbox = buildSandbox()
  const context = createContext(sandbox)

  // Run component script once to register the element
  new Script(scriptSource).runInContext(context)

  // Create two instances in the same context
  const createElFn = new Script(`
    (function(siteKey) {
      const el = new (customElements.get('managed-site-links'))();
      if (siteKey !== undefined) el.setAttribute('site-key', siteKey);
      return el;
    })
  `)

  const el1 = createElFn.runInContext(context)("twjsz666")
  const el2 = createElFn.runInContext(context)("twjsz666")

  if (typeof el1.connectedCallback === "function") el1.connectedCallback()
  if (typeof el2.connectedCallback === "function") el2.connectedCallback()

  await new Promise((resolve) => setTimeout(resolve, 50))

  // Each instance should have triggered one fetch = 2 total
  if (fetchCalls.length !== 2) {
    throw new Error(`two instances triggered ${fetchCalls.length} fetch calls, expected 2 (one per connection)`)
  }

  console.log("Test 8 passed: each instance fetches exactly once (one fetch per connection)")
}

// ---------------------------------------------------------------------------
// Test 9 — Component does not expose or fallback to any hardcoded link list
// ---------------------------------------------------------------------------
{
  const linksPayload = {
    links: [{ site_key: "dynamic", name: "Dynamic Only", domain: "d.example.com", url: "https://d.example.com/" }],
  }
  resetFetchState(linksPayload, false)

  const sandbox = buildSandbox()
  const context = createContext(sandbox)

  new Script(scriptSource).runInContext(context)

  const createElFn = new Script(`
    (function(siteKey) {
      const el = new (customElements.get('managed-site-links'))();
      if (siteKey !== undefined) el.setAttribute('site-key', siteKey);
      return el;
    })
  `)

  const el = createElFn.runInContext(context)("twjsz666")
  if (typeof el.connectedCallback === "function") el.connectedCallback()
  await new Promise((resolve) => setTimeout(resolve, 50))

  // The shadow root's initial template innerHTML must not contain any <a> tags
  const initialHtml = el.shadowRoot.__innerHTML
  if (/<a\b/i.test(initialHtml)) {
    throw new Error("component shadow template must not contain hardcoded <a> elements")
  }

  // All anchors must be created via document.createElement (tracked)
  if (sandbox._anchorTracker.length !== 1) {
    throw new Error(`expected exactly 1 dynamic anchor, got ${sandbox._anchorTracker.length}`)
  }

  console.log("Test 9 passed: no hardcoded fallback links in template")
}

// ---------------------------------------------------------------------------
// Test 10 — Reconnect safety: second connectedCallback does not re-attach
// shadow root and does not trigger a second fetch
// ---------------------------------------------------------------------------
{
  const linksPayload = {
    links: [{ site_key: "reconnect", name: "Reconnect", domain: "r.example.com", url: "https://r.example.com/" }],
  }
  resetFetchState(linksPayload, false)

  const sandbox = buildSandbox()
  const context = createContext(sandbox)

  new Script(scriptSource).runInContext(context)

  const createElFn = new Script(`
    (function(siteKey) {
      const el = new (customElements.get('managed-site-links'))();
      if (siteKey !== undefined) el.setAttribute('site-key', siteKey);
      return el;
    })
  `)

  const el = createElFn.runInContext(context)("twjsz666")

  // First connect
  if (typeof el.connectedCallback === "function") el.connectedCallback()

  // Simulate element being removed from and re-inserted into the DOM
  if (typeof el.disconnectedCallback === "function") el.disconnectedCallback()
  if (typeof el.connectedCallback === "function") el.connectedCallback()

  await new Promise((resolve) => setTimeout(resolve, 50))

  // attachShadow must be called exactly once (second connect must reuse existing shadow root)
  if (el._attachShadowCalls !== 1) {
    throw new Error(`expected 1 attachShadow call across reconnects, got ${el._attachShadowCalls}`)
  }

  // Exactly one fetch across reconnects (no duplicate fetch)
  if (fetchCalls.length !== 1) {
    throw new Error(`reconnect triggered ${fetchCalls.length} fetch calls, expected 1`)
  }

  // Shadow root must still be present and hold the rendered link
  if (!el.shadowRoot) {
    throw new Error("reconnect: shadow root must persist across reconnects")
  }
  if (sandbox._anchorTracker.length !== 1) {
    throw new Error(`reconnect: expected 1 rendered anchor, got ${sandbox._anchorTracker.length}`)
  }

  console.log("Test 10 passed: reconnect does not re-attach shadow or re-fetch")
}

// ---------------------------------------------------------------------------
// Test 11 — Fetch failure retry: on fetch error, _fetched is reset to false,
// so a reconnect triggers a new fetch attempt (TDD: fails before the fix)
// ---------------------------------------------------------------------------
{
  // First connect: fetch will fail
  resetFetchState(null, true)

  const sandbox = buildSandbox()
  const context = createContext(sandbox)

  new Script(scriptSource).runInContext(context)

  const createElFn = new Script(`
    (function(siteKey) {
      const el = new (customElements.get('managed-site-links'))();
      if (siteKey !== undefined) el.setAttribute('site-key', siteKey);
      return el;
    })
  `)

  const el = createElFn.runInContext(context)("twjsz666")

  // First connect — fetch fails
  if (typeof el.connectedCallback === "function") el.connectedCallback()
  await new Promise((resolve) => setTimeout(resolve, 50))

  // Should have exactly one failed fetch attempt
  if (fetchCalls.length !== 1) {
    throw new Error(`first connect (failing) triggered ${fetchCalls.length} fetch calls, expected 1`)
  }

  // Links area must be empty after failure
  if (sandbox._anchorTracker.length !== 0) {
    throw new Error(`after first failure: expected 0 anchors, got ${sandbox._anchorTracker.length}`)
  }
  const linksContainer = el.shadowRoot.querySelector('[data-links]')
  if (linksContainer.__children.length !== 0) {
    throw new Error("after first failure: links container must have no children")
  }

  // Now switch to success mode for the retry (without resetting fetchCalls)
  fetchShouldFail = false
  fetchResponse = {
    links: [{ site_key: "retry", name: "RetryLink", domain: "r.example.com", url: "https://r.example.com/" }],
  }

  // Simulate element removal and re-insertion
  if (typeof el.disconnectedCallback === "function") el.disconnectedCallback()
  if (typeof el.connectedCallback === "function") el.connectedCallback()
  await new Promise((resolve) => setTimeout(resolve, 50))

  // After reconnect, should have triggered a new fetch (2 total: 1 failed + 1 retry)
  if (fetchCalls.length !== 2) {
    throw new Error(
      `after reconnect (previously failed): expected 2 fetch calls (1 failed + 1 retry), got ${fetchCalls.length}. ` +
      `_fetched flag was likely NOT reset on failure.`
    )
  }

  // The retry fetch URL must be correct
  const retryUrl = fetchCalls[1].url
  if (!retryUrl.startsWith("/api/site-links") || !retryUrl.includes("site_key=twjsz666")) {
    throw new Error(`retry fetch URL incorrect: ${retryUrl}`)
  }

  // Shadow root must still exist (not re-attached)
  if (el._attachShadowCalls !== 1) {
    throw new Error(`expected 1 attachShadow call across failure+reconnect, got ${el._attachShadowCalls}`)
  }

  // After successful retry, the link must be rendered
  if (sandbox._anchorTracker.length !== 1) {
    throw new Error(`after retry: expected 1 rendered anchor, got ${sandbox._anchorTracker.length}`)
  }
  if (sandbox._anchorTracker[0].textContent !== "RetryLink") {
    throw new Error(`after retry: expected text "RetryLink", got "${sandbox._anchorTracker[0].textContent}"`)
  }

  console.log("Test 11 passed: fetch failure resets _fetched, reconnect triggers retry fetch")
}

console.log("All managed-site-links contract tests passed")

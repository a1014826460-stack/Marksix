import assert from "node:assert/strict"
import fs from "node:fs"
import vm from "node:vm"

const source = fs.readFileSync(
  "frontend/public/vendor/_shared/forced-announcement.js",
  "utf8",
)

function createStorage() {
  const values = new Map()
  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
    removeItem(key) {
      values.delete(key)
    },
    clear() {
      values.clear()
    },
  }
}

class Element {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase()
    this.children = []
    this.dataset = {}
    this.listeners = {}
    this.attributes = {}
    this.parentNode = null
    this.textContent = ""
    this.innerHTML = ""
    this.className = ""
  }

  appendChild(child) {
    child.parentNode = this
    this.children.push(child)
    return child
  }

  remove() {
    if (!this.parentNode) return
    this.parentNode.children = this.parentNode.children.filter((child) => child !== this)
    this.parentNode = null
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value)
  }

  addEventListener(name, handler) {
    this.listeners[name] = handler
  }

  dispatch(name) {
    if (this.listeners[name]) this.listeners[name]({ target: this })
  }

  findByAction(action) {
    if (this.dataset.action === action) return this
    for (const child of this.children) {
      const found = child.findByAction(action)
      if (found) return found
    }
    return null
  }
}

function createEnvironment(announcement, options = {}) {
  const sessionStorage = createStorage()
  const localStorage = createStorage()
  const documentListeners = {}
  const document = {
    readyState: "loading",
    body: new Element("body"),
    head: new Element("head"),
    createElement(tagName) {
      return new Element(tagName)
    },
    getElementById() {
      return null
    },
    addEventListener(name, handler) {
      documentListeners[name] = handler
    },
  }
  if (options.bodySiteKey !== false) document.body.dataset.siteKey = options.bodySiteKey || "twssz"
  const expectedUrl = options.expectedUrl || `/api/public/forced-announcement?site_key=${document.body.dataset.siteKey}`

  let fetchCount = 0
  const window = {
    document,
    sessionStorage,
    localStorage,
    URLSearchParams,
    location: { pathname: options.pathname || "/" },
    fetch: async (url, options) => {
      fetchCount += 1
      assert.equal(url, expectedUrl)
      assert.equal(options.cache, "no-store")
      return { ok: true, json: async () => announcement }
    },
  }
  window.window = window
  window.parent = options.parent || window

  vm.runInNewContext(source, {
    window,
    document,
    URLSearchParams,
    Promise,
  })

  return {
    window,
    document,
    documentListeners,
    sessionStorage,
    localStorage,
    fetchCount: () => fetchCount,
  }
}

const announcement = {
  id: 1,
  version: "version-one",
  title: "开奖公告",
  html: "<p>请确认</p>",
  starts_at: "2026-08-11T22:32:00+08:00",
  ends_at: null,
}

{
  const env = createEnvironment(announcement, {
    bodySiteKey: false,
    pathname: "/twssz",
    expectedUrl: "/api/public/forced-announcement?site_key=twssz",
  })
  const overlay = await env.window.ForcedAnnouncement.mount()
  assert.ok(overlay)
}

{
  const vendorSiteKeys = {
    shengshi8800: "shengshi8800",
    twsaimahui: "twsaimahui",
    "twcaibawang.com": "twcaibawang",
    twjinniu: "twjinniu",
    "twcf888.com": "twcf888",
    twssz: "twssz",
    twbst528: "twbst528",
    twjsz666: "twjsz666",
    twwanli: "twwanli",
    twsyw: "twsyw",
  }

  for (const [vendorDirectory, siteKey] of Object.entries(vendorSiteKeys)) {
    const env = createEnvironment(announcement, {
      bodySiteKey: "stale-site-key",
      pathname: `/vendor/${vendorDirectory}/nested/page.html`,
      expectedUrl: `/api/public/forced-announcement?site_key=${siteKey}`,
    })
    const overlay = await env.window.ForcedAnnouncement.mount()
    assert.ok(overlay)
  }
}

{
  const env = createEnvironment(announcement, {
    parent: { ForcedAnnouncement: { mount() {} } },
  })
  env.documentListeners.DOMContentLoaded()
  await Promise.resolve()
  assert.equal(env.fetchCount(), 0)
}

{
  const env = createEnvironment(announcement)
  const overlay = await env.window.ForcedAnnouncement.mount()
  assert.ok(overlay)
  assert.equal(overlay.listeners.click, undefined)
  assert.equal(env.documentListeners.keydown, undefined)

  const close = overlay.findByAction("session-close")
  assert.ok(close)
  close.dispatch("click")
  assert.equal(
    env.sessionStorage.getItem("forced-announcement:session:version-one"),
    "1",
  )
  assert.equal(env.window.ForcedAnnouncement.shouldDisplay(announcement), false)

  env.sessionStorage.clear()
  assert.equal(env.window.ForcedAnnouncement.shouldDisplay(announcement), true)
}

{
  const env = createEnvironment(announcement)
  const overlay = await env.window.ForcedAnnouncement.mount()
  const confirm = overlay.findByAction("confirm")
  assert.ok(confirm)
  confirm.dispatch("click")
  assert.equal(
    env.localStorage.getItem("forced-announcement:confirmed:version-one"),
    "1",
  )
  assert.equal(env.window.ForcedAnnouncement.shouldDisplay(announcement), false)
  assert.equal(
    env.window.ForcedAnnouncement.shouldDisplay({ ...announcement, version: "version-two" }),
    true,
  )
}

console.log("forced announcement runtime contract passed")

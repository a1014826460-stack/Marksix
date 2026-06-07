"use client"

import { useEffect, useRef, useState } from "react"

const VENDOR_HOME_URL = "/vendor/twcf888.com/index.html"
const FALLBACK_HEIGHT = 1600

type StickyNavLink = {
  href: string
  label: string
}

type StickyNavRow = StickyNavLink[]

export function Twcf888HomeClient() {
  const frameRef = useRef<HTMLIFrameElement | null>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)
  const intervalRef = useRef<number | null>(null)
  const [frameHeight, setFrameHeight] = useState(FALLBACK_HEIGHT)
  const [navRows, setNavRows] = useState<StickyNavRow[]>([])
  const [navVisible, setNavVisible] = useState(false)
  const [navHeight, setNavHeight] = useState(0)
  const [navFrameLeft, setNavFrameLeft] = useState(0)
  const [navFrameWidth, setNavFrameWidth] = useState(0)

  useEffect(() => {
    const frame = frameRef.current
    if (!frame) return

    const disconnectObserver = () => {
      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect()
        resizeObserverRef.current = null
      }
    }

    const clearHeightTimer = () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    const collectNavData = () => {
      try {
        const doc = frame.contentDocument
        const nav = doc?.getElementById("nav2")
        if (!nav) return

        const nextRows: StickyNavRow[] = Array.from(nav.querySelectorAll(":scope > ul"))
          .map((list) =>
            Array.from(list.querySelectorAll("a"))
              .map((link) => ({
                href: link.getAttribute("href") || "",
                label: (link.textContent || "").trim(),
              }))
              .filter((item) => item.href.startsWith("#") && item.label)
          )
          .filter((row) => row.length > 0)

        setNavRows(nextRows)
        setNavHeight(nav.getBoundingClientRect().height || nav.offsetHeight || 0)
      } catch {
        // Ignore same-origin access races while the iframe is still loading.
      }
    }

    const updateStickyMetrics = () => {
      try {
        const doc = frame.contentDocument
        const nav = doc?.getElementById("nav2")
        if (!doc || !nav) return

        const frameRect = frame.getBoundingClientRect()
        const navRect = nav.getBoundingClientRect()
        const nextNavHeight = navRect.height || nav.offsetHeight || 0
        const nextNavOffsetTop = nav.offsetTop || 0
        const shouldFix = frameRect.top + nextNavOffsetTop <= 0

        setNavHeight(nextNavHeight)
        setNavFrameLeft(frameRect.left + navRect.left)
        setNavFrameWidth(navRect.width)
        setNavVisible(shouldFix)
      } catch {
        // Ignore same-origin access races while the iframe is still loading.
      }
    }

    const syncHeight = () => {
      try {
        const doc = frame.contentDocument
        const body = doc?.body
        const root = doc?.documentElement
        if (!body || !root) return
        const nextHeight = Math.max(
          body.scrollHeight,
          body.offsetHeight,
          root.scrollHeight,
          root.offsetHeight,
          root.clientHeight
        )
        if (nextHeight > 0) {
          setFrameHeight(nextHeight)
        }
        collectNavData()
        updateStickyMetrics()
      } catch {
        // Ignore same-origin access races while the iframe is still loading.
      }
    }

    const attachResizeObserver = () => {
      disconnectObserver()
      try {
        const doc = frame.contentDocument
        const body = doc?.body
        const root = doc?.documentElement
        if (!body || !root || typeof ResizeObserver === "undefined") {
          return
        }

        const observer = new ResizeObserver(() => {
          syncHeight()
        })
        observer.observe(body)
        observer.observe(root)
        resizeObserverRef.current = observer
      } catch {
        // Ignore observer attachment failures and keep the interval fallback.
      }
    }

    const handleLoad = () => {
      syncHeight()
      attachResizeObserver()
      collectNavData()
      updateStickyMetrics()
    }

    frame.addEventListener("load", handleLoad)
    window.addEventListener("scroll", updateStickyMetrics, { passive: true })
    window.addEventListener("resize", updateStickyMetrics)
    syncHeight()
    intervalRef.current = window.setInterval(syncHeight, 1000)

    return () => {
      frame.removeEventListener("load", handleLoad)
      window.removeEventListener("scroll", updateStickyMetrics)
      window.removeEventListener("resize", updateStickyMetrics)
      disconnectObserver()
      clearHeightTimer()
    }
  }, [])

  function handleStickyNavClick(anchorId: string) {
    const frame = frameRef.current
    if (!frame) return

    try {
      const doc = frame.contentDocument
      const target = doc?.getElementById(anchorId)
      if (!doc || !target) return

      const frameTop = frame.getBoundingClientRect().top + window.scrollY
      const offset = (navHeight || 0) + 8
      const top = Math.max(0, frameTop + target.offsetTop - offset)
      window.scrollTo({ top, behavior: "smooth" })
    } catch {
      // Ignore same-origin access races while the iframe is still loading.
    }
  }

  return (
    <main className="twcf888-shell">
      <style jsx>{`
        .twcf888-shell {
          width: 100%;
          min-height: 100vh;
          background: #ffffff;
        }

        .twcf888-sticky-nav {
          position: fixed;
          top: 0;
          z-index: 999;
          box-sizing: border-box;
          padding: 2px;
          background: #fff;
          box-shadow: 0 5px 10px rgba(0, 0, 0, 0.1);
        }

        .twcf888-sticky-nav ul {
          display: flex;
          justify-content: space-between;
          margin: 0;
          padding: 2px 0;
          list-style: none;
        }

        .twcf888-sticky-nav li {
          width: 100%;
          box-sizing: border-box;
          padding: 0 2px;
        }

        .twcf888-sticky-nav a {
          display: block;
          padding: 4px 0;
          text-align: center;
          color: #fff;
          border-radius: 50px;
          background: #237575;
          text-decoration: none;
          cursor: pointer;
          font: 13px "Helvetica Neue", Helvetica, STHeiTi, sans-serif;
        }

        .twcf888-sticky-nav a:hover {
          background: #da183b;
        }

        .twcf888-frame {
          display: block;
          width: 100%;
          border: 0;
          background: #ffffff;
        }

        @media (min-width: 800px) {
          .twcf888-sticky-nav {
            padding: 4px;
          }

          .twcf888-sticky-nav ul {
            padding: 2px 0;
          }

          .twcf888-sticky-nav li {
            padding: 0 4px;
          }

          .twcf888-sticky-nav a {
            padding: 8px 0;
            font-size: 14px;
          }
        }
      `}</style>
      {navVisible && navRows.length > 0 ? (
        <div
          className="twcf888-sticky-nav"
          style={{
            left: `${Math.max(0, navFrameLeft)}px`,
            width: `${navFrameWidth || 0}px`,
          }}
        >
          {navRows.map((row, rowIndex) => (
            <ul key={rowIndex}>
              {row.map((item) => {
                const anchorId = item.href.slice(1)
                return (
                  <li key={`${rowIndex}-${anchorId}`}>
                    <a
                      href={item.href}
                      onClick={(event) => {
                        event.preventDefault()
                        handleStickyNavClick(anchorId)
                      }}
                    >
                      {item.label}
                    </a>
                  </li>
                )
              })}
            </ul>
          ))}
        </div>
      ) : null}
      <iframe
        ref={frameRef}
        className="twcf888-frame"
        title="Twcf888 Home"
        src={VENDOR_HOME_URL}
        scrolling="no"
        style={{ height: `${frameHeight}px` }}
      />
    </main>
  )
}

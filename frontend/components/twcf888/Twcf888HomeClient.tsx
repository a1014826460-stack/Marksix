"use client"

import { useEffect, useRef, useState } from "react"

const VENDOR_HOME_URL = "/vendor/twcf888.com/index.html"
const FALLBACK_HEIGHT = 1600

export function Twcf888HomeClient() {
  const frameRef = useRef<HTMLIFrameElement | null>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)
  const intervalRef = useRef<number | null>(null)
  const [frameHeight, setFrameHeight] = useState(FALLBACK_HEIGHT)

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
    }

    frame.addEventListener("load", handleLoad)
    syncHeight()
    intervalRef.current = window.setInterval(syncHeight, 1000)

    return () => {
      frame.removeEventListener("load", handleLoad)
      disconnectObserver()
      clearHeightTimer()
    }
  }, [])

  return (
    <main className="twcf888-shell">
      <style jsx>{`
        .twcf888-shell {
          width: 100%;
          min-height: 100vh;
          background: #ffffff;
        }

        .twcf888-frame {
          display: block;
          width: 100%;
          border: 0;
          background: #ffffff;
        }
      `}</style>
      <iframe
        ref={frameRef}
        className="twcf888-frame"
        title="台湾创富网"
        src={VENDOR_HOME_URL}
        scrolling="no"
        style={{ height: `${frameHeight}px` }}
      />
    </main>
  )
}

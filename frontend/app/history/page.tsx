"use client"

import { Suspense, useEffect, useMemo, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import {
  LOTTERY_TYPE_NAMES,
  type DrawHistoryBall,
  type DrawHistoryResponse,
  normalizeHistorySort,
  normalizeLotteryType,
} from "@/lib/draw-history"

const LOTTERY_OPTIONS = [
  { type: 3 as const, label: "台湾彩" },
  { type: 2 as const, label: "澳门彩" },
  { type: 1 as const, label: "香港彩" },
]

const DEFAULT_PAGE_SIZE = 20
const PAGE_SIZE_OPTIONS = [10, 20, 30, 50]

const DEFAULT_VISIBLE_OPTIONS = {
  number: true,
  zodiac: true,
  wave: false,
  oddEven: false,
  animal: false,
}

type VisibleOptions = typeof DEFAULT_VISIBLE_OPTIONS

function ballClass(color: string) {
  if (color === "red") return "ball-red"
  if (color === "blue") return "ball-blue"
  if (color === "green") return "ball-green"
  return ""
}

function elementClass(element: string) {
  if (element === "金") return "wx-jin"
  if (element === "木") return "wx-mu"
  if (element === "水") return "wx-shui"
  if (element === "火") return "wx-huo"
  if (element === "土") return "wx-tu"
  return ""
}

function colorTextClass(color: string) {
  if (color === "red") return "text-red"
  if (color === "blue") return "text-blue"
  if (color === "green") return "text-green"
  return "text-black"
}

function normalizePositiveInteger(value: string | null, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

function normalizePageSize(value: string | null) {
  const parsed = normalizePositiveInteger(value, DEFAULT_PAGE_SIZE)
  return PAGE_SIZE_OPTIONS.includes(parsed) ? parsed : DEFAULT_PAGE_SIZE
}

function renderBall(ball: DrawHistoryBall | undefined, key: string, visible: VisibleOptions) {
  if (!ball) return null

  return (
    <li key={key}>
      <dl>
        <dt className={ballClass(ball.color)} style={{ display: visible.number ? undefined : "none" }}>
          {ball.value}
        </dt>
        <dd style={{ display: visible.zodiac ? undefined : "none" }}>
          {ball.zodiac}
          <span className="grey-txt">/</span>
          <span className={elementClass(ball.element)}>{ball.element}</span>
        </dd>
        <dd style={{ display: visible.wave ? undefined : "none" }}>
          <span className={colorTextClass(ball.color)}>{ball.wave}</span>
          <span className="grey-txt">/</span>
          <span className="text-black">{ball.size}</span>
        </dd>
        <dd style={{ display: visible.oddEven ? undefined : "none" }}>
          <span className="text-pink">{ball.oddEven}</span>
          <span className="grey-txt">/</span>
          <span className="text-yellow">{ball.combinedOddEven}</span>
        </dd>
        <dd style={{ display: visible.animal ? undefined : "none" }}>
          <span className="text-brown">{ball.animalType}</span>
          <span className="grey-txt">/</span>
          <span className="text-caolv">{ball.sumOddEven}</span>
        </dd>
      </dl>
    </li>
  )
}

function HistoryPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const lotteryType = normalizeLotteryType(searchParams.get("type") || searchParams.get("lottery_type"))
  const currentYear = Number(searchParams.get("year")) || new Date().getFullYear()
  const sort = normalizeHistorySort(searchParams.get("sort"))
  const currentPage = normalizePositiveInteger(searchParams.get("page"), 1)
  const currentPageSize = normalizePageSize(searchParams.get("page_size") || searchParams.get("limit"))
  const [payload, setPayload] = useState<DrawHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [visible, setVisible] = useState<VisibleOptions>(DEFAULT_VISIBLE_OPTIONS)

  const lotteryName = LOTTERY_TYPE_NAMES[lotteryType]
  const years = payload?.years?.length ? payload.years : [currentYear]
  const page = payload?.page || currentPage
  const pageSize = payload?.page_size || currentPageSize
  const total = payload?.total || 0
  const totalPages = payload?.total_pages || 1

  const title = useMemo(() => `${lotteryName}开奖记录`, [lotteryName])

  function updateQuery(next: Record<string, string | number>, options?: { keepPage?: boolean }) {
    const params = new URLSearchParams(searchParams.toString())
    Object.entries(next).forEach(([key, value]) => params.set(key, String(value)))
    if (!options?.keepPage && !("page" in next)) {
      params.set("page", "1")
    }
    router.push(`/history?${params.toString()}`)
  }

  useEffect(() => {
    const controller = new AbortController()
    async function loadHistory() {
      setLoading(true)
      try {
        const query = new URLSearchParams({
          lottery_type: String(lotteryType),
          year: String(currentYear),
          sort,
          page: String(currentPage),
          page_size: String(currentPageSize),
        })
        const response = await fetch(`/api/draw-history?${query.toString()}`, {
          cache: "no-store",
          signal: controller.signal,
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        setPayload((await response.json()) as DrawHistoryResponse)
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    loadHistory().catch(() => {
      if (!controller.signal.aborted) setPayload(null)
    })
    return () => controller.abort()
  }, [currentPage, currentPageSize, currentYear, lotteryType, sort])

  return (
    <>
      <link rel="stylesheet" href="/vendor/admin-history/static/css/bootstrap.min.css" />
      <link rel="stylesheet" href="/vendor/admin-history/static/css/kj.css" />
      <link rel="stylesheet" href="/vendor/admin-history/static/css/pintuer.css" />
      <link rel="stylesheet" href="/vendor/admin-history/static/css/style1.css" />
      <div className="history-page">
        <div className="main">
          <div className="head">
            <span style={{ position: "absolute", left: 12 }}>
              <a href={`/?t=${lotteryType}`} style={{ color: "white" }}>
                返回上级
              </a>
            </span>
            <span className="sel-year">{title}</span>
          </div>
          <div className="layout">
            <div className="menu fixed-top history-fixed-menu">
              <div className="inner main">
                <span style={{ position: "absolute", top: 12, left: 12 }}>
                  <a href={`/?t=${lotteryType}`} style={{ color: "#fff" }}>
                    返回上级
                  </a>
                </span>
                <dl>
                  <dt className="line-60">选择年份</dt>
                  <dd className="years-list" data-open="on">
                    <ul>
                      {years.map((year) => (
                        <li key={year}>
                          <button
                            className={year === currentYear ? "history-filter active" : "history-filter"}
                            type="button"
                            onClick={() => updateQuery({ year })}
                          >
                            {year}年
                          </button>
                        </li>
                      ))}
                    </ul>
                  </dd>
                </dl>
              </div>
              <div className="history-game-tabs">
                {LOTTERY_OPTIONS.map((option) => (
                  <button
                    key={option.type}
                    className={option.type === lotteryType ? "history-game-tab active" : "history-game-tab"}
                    type="button"
                    onClick={() => updateQuery({ type: option.type })}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <div>
                <a className="badge bg-gray radius-none text-white active_on">开奖记录</a>
              </div>
              <article className="infos padding-b1">
                <div className="inner">
                  <header id="topbartit" className="title">
                    <div className="loading" style={{ display: loading ? undefined : "none" }} />
                    <dl className="clearfix">
                      <dd className="left">
                        <label>查看选项：</label>
                        {[
                          ["number", "平码/特码"],
                          ["zodiac", "生肖/五行"],
                          ["wave", "波色/大小"],
                          ["oddEven", "单双/合单双"],
                          ["animal", "家禽野兽/总和单双"],
                        ].map(([key, label]) => (
                          <span key={key}>
                            <input
                              className="history"
                              type="checkbox"
                              checked={visible[key as keyof VisibleOptions]}
                              onChange={() =>
                                setVisible((current) => ({
                                  ...current,
                                  [key]: !current[key as keyof VisibleOptions],
                                }))
                              }
                            />{" "}
                            <a
                              className="history"
                              href="#"
                              onClick={(event) => {
                                event.preventDefault()
                                setVisible((current) => ({
                                  ...current,
                                  [key]: !current[key as keyof VisibleOptions],
                                }))
                              }}
                            >
                              {label}
                            </a>{" "}
                          </span>
                        ))}
                        <br />
                        <label className="margin-big-top">排序方式：</label>
                        <input name="history" type="radio" checked={sort === "l"} readOnly />{" "}
                        <a onClick={() => updateQuery({ sort: "l" })}>落球顺序</a> &nbsp;
                        <input name="history" type="radio" checked={sort === "d"} readOnly />{" "}
                        <a onClick={() => updateQuery({ sort: "d" })}>大小顺序</a>
                      </dd>
                    </dl>
                  </header>
                </div>
              </article>
            </div>
            <div className="clearfix" />
            <div className="gexian" />
            <div className="content">
              <div className="main">
                <article className="table-area" id="tableArea">
                  <div className="cgi-wrap">
                    <div id="whiteBox" className="white-box" style={{ opacity: loading ? 0.45 : 1 }}>
                      {payload?.items?.map((item) => (
                        <div key={`${item.date}-${item.issue}`}>
                          <div className="kj-tit">
                            {`${payload.lottery_name}开奖记录 ${item.date} 第`}
                            <span className="text-blue text-strong">{item.issue}</span>期
                          </div>
                          <div className="kj-box">
                            <ul className="clearfix">
                              {item.balls.map((ball, index) => renderBall(ball, `${item.issue}-${index}`, visible))}
                              <li className="kj-jia">
                                <dl>
                                  <dt />
                                </dl>
                              </li>
                              {renderBall(item.specialBall, `${item.issue}-special`, visible)}
                            </ul>
                          </div>
                        </div>
                      ))}
                      {!loading && !payload?.items?.length && (
                        <div className="history-empty">暂无开奖记录</div>
                      )}
                    </div>
                    <div className="history-pagination">
                      <button
                        type="button"
                        disabled={loading || page <= 1}
                        onClick={() => updateQuery({ page: page - 1 }, { keepPage: true })}
                      >
                        上一页
                      </button>
                      <span>
                        第 {page} / {totalPages} 页，共 {total} 条
                      </span>
                      <button
                        type="button"
                        disabled={loading || page >= totalPages}
                        onClick={() => updateQuery({ page: page + 1 }, { keepPage: true })}
                      >
                        下一页
                      </button>
                      <label>
                        每页
                        <select
                          value={pageSize}
                          disabled={loading}
                          onChange={(event) => updateQuery({ page_size: event.target.value })}
                        >
                          {PAGE_SIZE_OPTIONS.map((size) => (
                            <option key={size} value={size}>
                              {size}条
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                  </div>
                </article>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default function DrawHistoryPage() {
  return (
    <Suspense fallback={null}>
      <HistoryPageContent />
    </Suspense>
  )
}

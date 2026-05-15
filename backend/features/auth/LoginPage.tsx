"use client"

import type { FormEvent } from "react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi, jsonBody, setAdminToken } from "@/lib/admin-api"
import { Field } from "@/features/shared/Field"
import { formValue } from "@/features/shared/form-helpers"

// 诗句数据
const verseLines = [
  "赵客缦胡缨，吴钩霜雪明",
  "银鞍照白马，飒沓如流星",
  "十步杀一人，千里不留行",
  "事了拂衣去，深藏身与名",
]

/** 递增延迟：失败次数 → 秒数（1, 2, 4, 8, 16 封顶） */
function retryDelaySeconds(failureCount: number): number {
  return Math.min(2 ** (failureCount - 1), 16)
}

/** 格式化剩余秒数为 mm:ss */
function formatCountdown(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

export function LoginPage() {
  const router = useRouter()
  const [message, setMessage] = useState("")
  const [messageIsWarning, setMessageIsWarning] = useState(false)

  // 验证码
  const [captchaImage, setCaptchaImage] = useState("")
  const [captchaLoading, setCaptchaLoading] = useState(false)

  // 锁定状态
  const [locked, setLocked] = useState(false)
  const [lockCountdown, setLockCountdown] = useState(0)
  const lockTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 本地递增延迟
  const [submitting, setSubmitting] = useState(false)
  const localFailuresRef = useRef(0)
  const lastSubmitRef = useRef(0)

  // 获取验证码
  const fetchCaptcha = useCallback(async () => {
    setCaptchaLoading(true)
    try {
      const data = await adminApi<{ image: string; expires_in_seconds: number }>(
        "/auth/captcha",
      )
      setCaptchaImage(data.image)
    } catch {
      setCaptchaImage("")
    } finally {
      setCaptchaLoading(false)
    }
  }, [])

  // 首次加载获取验证码
  useEffect(() => {
    fetchCaptcha()
    return () => {
      if (lockTimerRef.current) clearInterval(lockTimerRef.current)
    }
  }, [fetchCaptcha])

  // 锁定倒计时
  useEffect(() => {
    if (locked && lockCountdown > 0) {
      lockTimerRef.current = setInterval(() => {
        setLockCountdown((prev) => {
          if (prev <= 1) {
            setLocked(false)
            localFailuresRef.current = 0
            fetchCaptcha()
            return 0
          }
          return prev - 1
        })
      }, 1000)
      return () => {
        if (lockTimerRef.current) clearInterval(lockTimerRef.current)
      }
    }
  }, [locked, lockCountdown, fetchCaptcha])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    // 立即保存 form 引用 —— React 合成事件在 await 后会置空 currentTarget
    const form = event.currentTarget

    // 节流：1 秒内最多一次请求
    const now = Date.now()
    if (now - lastSubmitRef.current < 1000) return
    lastSubmitRef.current = now

    // 递增延迟
    if (submitting) return
    const delay = retryDelaySeconds(localFailuresRef.current)
    if (delay > 0 && localFailuresRef.current > 0) {
      setSubmitting(true)
      setMessage(`请等待 ${delay} 秒后再试...`)
      setMessageIsWarning(true)
      await new Promise((r) => setTimeout(r, delay * 1000))
    }

    setMessage("")
    setMessageIsWarning(false)

    try {
      const result = await adminApi<{ token: string }>("/auth/login", {
        method: "POST",
        body: jsonBody({
          username: formValue(form, "username"),
          password: formValue(form, "password"),
          captcha: formValue(form, "captcha"),
        }),
      })
      // 登录成功
      localFailuresRef.current = 0
      setAdminToken(result.token)
      router.replace("/")
    } catch (error) {
      const err = error as Error & { locked?: boolean; attemptCount?: number; maxAttempts?: number }
      setMessage(err.message || "登录失败")
      setMessageIsWarning(false)

      // 被锁定
      if (err.locked) {
        setLocked(true)
        setLockCountdown(15 * 60) // 15 分钟
        setMessage(err.message)
        return
      }

      // 失败递增
      localFailuresRef.current += 1

      // 刷新验证码
      fetchCaptcha()
      // 清空验证码输入
      const captchaInput = form.querySelector<HTMLInputElement>('[name="captcha"]')
      if (captchaInput) captchaInput.value = ""
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      {/* 动画样式注入 */}
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px); filter: blur(4px); }
          to   { opacity: 1; transform: translateY(0); filter: blur(0); }
        }
        @keyframes shimmer {
          0%   { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        @keyframes floatGlow {
          0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.08; }
          50%      { transform: translate(-30%, -60%) scale(1.3); opacity: 0.18; }
        }
        @keyframes meteor {
          0%   { transform: translateX(-100%) translateY(0); opacity: 0; }
          10%  { opacity: 1; }
          30%  { opacity: 0; }
          100% { transform: translateX(300%) translateY(-20px); opacity: 0; }
        }
      `}</style>

      <main className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm p-6">
          <h1 className="text-xl font-semibold">彩票软件后台登录</h1>

      {/* 诗句特效区域 */}
      <div className="relative mt-1 overflow-hidden rounded-lg px-1 py-2 group">
        {/* 背景光晕 */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 200px 150px at 30% 40%, rgba(148,163,184,0.08) 0%, transparent 70%), " +
              "radial-gradient(ellipse 100px 75px at 70% 60%, rgba(203,213,225,0.06) 0%, transparent 70%)",
            animation: "floatGlow 8s ease-in-out infinite",
          }}
        />
        {/* 流星装饰 */}
        <div
          className="pointer-events-none absolute left-0 top-1/3 h-px w-16"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)",
            animation: "meteor 4s ease-in-out infinite",
            animationDelay: "3s",
          }}
        />

        {/* 诗句逐行 – 增加了 text-center */}
        <div className="relative space-y-0.5 text-center">
          {verseLines.map((line, index) => {
            const isLastLine = index === verseLines.length - 1

            return (
              <p
                key={index}
                className="text-sm leading-relaxed tracking-wider select-none"
                style={{
                  // 扫光层 + 更深的文字基底渐变
                  backgroundImage: `
                    linear-gradient(
                      90deg,
                      transparent 0%,
                      rgba(255,255,255,0.15) 45%,
                      rgba(255,255,255,0.55) 50%,
                      rgba(255,255,255,0.15) 55%,
                      transparent 100%
                    ),
                    linear-gradient(
                      to right,
                      #64748b,
                      #334155,
                      #0f172a,
                      #334155,
                      #64748b
                    )
                  `,
                  backgroundSize: "200% 100%, 100% 100%",
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  color: "transparent",
                  animation: `
                    fadeInUp 0.6s ease-out ${index * 0.35}s both,
                    shimmer ${3 + index * 0.2}s ease-in-out ${2 + index * 0.3}s infinite
                  `,
                  ...(isLastLine && {
                    opacity: 0.4,
                    filter: "blur(1.5px)",
                    transition: "opacity 0.8s ease, filter 0.8s ease",
                  }),
                }}
              >
                {line}
              </p>
            )
          })}
        </div>

        {/* 最后一行 hover 显现控制 */}
        <style>{`
          .group:hover p:last-child {
            opacity: 1 !important;
            filter: blur(0) !important;
          }
        `}</style>
      </div>

          {/* 锁定遮罩 */}
          {locked && (
            <div className="mt-3 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-950 dark:text-red-100">
              <p className="font-semibold">设备已临时锁定</p>
              <p className="mt-1">
                因多次尝试失败，该设备已被临时锁定，请{" "}
                <span className="font-mono font-bold">{formatCountdown(lockCountdown)}</span>{" "}
                后再试。
              </p>
            </div>
          )}

          <form className="mt-5 space-y-3" onSubmit={submit}>
            <Field label="用户名">
              <Input
                name="username"
                defaultValue="admin"
                autoComplete="username"
                disabled={locked}
              />
            </Field>
            <Field label="密码">
              <Input
                name="password"
                type="password"
                defaultValue="admin123"
                autoComplete="current-password"
                disabled={locked}
              />
            </Field>

            {/* 验证码 */}
            <Field label="验证码">
              <div className="flex gap-2">
                <Input
                  name="captcha"
                  className="flex-1"
                  placeholder="请输入验证码"
                  autoComplete="off"
                  maxLength={4}
                  disabled={locked}
                />
                <button
                  type="button"
                  className="h-9 w-[100px] flex-shrink-0 overflow-hidden rounded-md border"
                  onClick={fetchCaptcha}
                  disabled={locked || captchaLoading}
                  title="点击刷新验证码"
                >
                  {captchaImage ? (
                    <img
                      src={captchaImage}
                      alt="验证码"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="flex h-full items-center justify-center text-xs text-muted-foreground">
                      {captchaLoading ? "加载中..." : "获取验证码"}
                    </span>
                  )}
                </button>
              </div>
            </Field>

            {message ? (
              <div
                className={
                  messageIsWarning
                    ? "rounded-md border border-blue-300 bg-blue-50 px-4 py-2.5 text-sm font-medium text-blue-800 shadow-sm dark:border-blue-700 dark:bg-blue-950 dark:text-blue-100"
                    : "rounded-md border border-amber-300 bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-900 shadow-sm dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
                }
              >
                <span className="mr-2 text-xs opacity-60">
                  [{new Date().toLocaleTimeString("zh-CN", { hour12: false })}]
                </span>
                {message}
              </div>
            ) : null}
            <Button className="w-full" type="submit" disabled={locked || submitting}>
              {submitting ? "请稍候..." : locked ? `已锁定 ${formatCountdown(lockCountdown)}` : "登录"}
            </Button>
          </form>
        </Card>
      </main>
    </>
  )
}

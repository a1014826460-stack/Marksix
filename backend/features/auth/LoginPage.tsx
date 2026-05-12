"use client"

import type { FormEvent } from "react"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { adminApi, jsonBody, setAdminToken } from "@/lib/admin-api"
import { Field } from "@/features/shared/Field"
import { AdminNotice } from "@/features/shared/AdminNotice"
import { formValue } from "@/features/shared/form-helpers"

// 诗句数据
const verseLines = [
  "赵客缦胡缨，吴钩霜雪明",
  "银鞍照白马，飒沓如流星",
  "十步杀一人，千里不留行",
  "事了拂衣去，深藏身与名",
]

export function LoginPage() {
  const router = useRouter()
  const [message, setMessage] = useState("")

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    try {
      const result = await adminApi<{ token: string }>("/auth/login", {
        method: "POST",
        body: jsonBody({
          username: formValue(form, "username"),
          password: formValue(form, "password"),
        }),
      })
      setAdminToken(result.token)
      router.replace("/")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败")
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

          <form className="mt-5 space-y-3" onSubmit={submit}>
            <Field label="用户名">
              <Input name="username" defaultValue="admin" autoComplete="username" />
            </Field>
            <Field label="密码">
              <Input
                name="password"
                type="password"
                defaultValue="admin123"
                autoComplete="current-password"
              />
            </Field>
            <AdminNotice message={message} />
            <Button className="w-full" type="submit">
              登录
            </Button>
          </form>
        </Card>
      </main>
    </>
  )
}

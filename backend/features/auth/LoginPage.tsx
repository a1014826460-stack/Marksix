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
    <main className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm p-6">
        <h1 className="text-xl font-semibold">彩票软件后台登录</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          默认账号：admin，默认密码：admin123。上线后请立即修改。
        </p>
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
  )
}

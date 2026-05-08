export type DrawHistoryBall = {
  value: string
  color: "red" | "blue" | "green" | string
  zodiac: string
  element: string
  wave?: string
  size?: string
  oddEven?: string
  combinedOddEven?: string
  animalType?: string
  sumOddEven?: string
}

export type DrawHistoryItem = {
  issue: string
  date: string
  title: string
  balls: DrawHistoryBall[]
  specialBall?: DrawHistoryBall
}

export type DrawHistoryResponse = {
  lottery_type: 1 | 2 | 3
  lottery_name: string
  year: number
  sort: "l" | "d"
  years: number[]
  page: number
  page_size: number
  total: number
  total_pages: number
  items: DrawHistoryItem[]
}

export const LOTTERY_TYPE_NAMES: Record<1 | 2 | 3, string> = {
  1: "香港彩",
  2: "澳门彩",
  3: "台湾彩",
}

export function normalizeLotteryType(value: string | number | null | undefined): 1 | 2 | 3 {
  const parsed = Number(value)
  if (parsed === 1 || parsed === 2 || parsed === 3) return parsed
  return 3
}

export function normalizeHistorySort(value: string | null | undefined): "l" | "d" {
  return value === "d" ? "d" : "l"
}

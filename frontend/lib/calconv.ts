interface LunarCalEntry {
  BaseDays: number
  Intercalation: number
  BaseWeekday: number
  BaseKanChih: number
  MonthDays: number[]
}

const FIRST_YEAR = 1998
const LAST_YEAR = 2032

const LUNAR_CAL: LunarCalEntry[] = [
  { BaseDays: 27, Intercalation: 5, BaseWeekday: 3, BaseKanChih: 43, MonthDays: [1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1] },
  { BaseDays: 46, Intercalation: 0, BaseWeekday: 4, BaseKanChih: 48, MonthDays: [1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1] },
  { BaseDays: 35, Intercalation: 0, BaseWeekday: 5, BaseKanChih: 53, MonthDays: [1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1] },
  { BaseDays: 23, Intercalation: 4, BaseWeekday: 0, BaseKanChih: 59, MonthDays: [1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 42, Intercalation: 0, BaseWeekday: 1, BaseKanChih: 4, MonthDays: [1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 31, Intercalation: 0, BaseWeekday: 2, BaseKanChih: 9, MonthDays: [1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0] },
  { BaseDays: 21, Intercalation: 2, BaseWeekday: 3, BaseKanChih: 14, MonthDays: [0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 39, Intercalation: 0, BaseWeekday: 5, BaseKanChih: 20, MonthDays: [0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 28, Intercalation: 7, BaseWeekday: 6, BaseKanChih: 25, MonthDays: [1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1] },
  { BaseDays: 48, Intercalation: 0, BaseWeekday: 0, BaseKanChih: 30, MonthDays: [0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 1] },
  { BaseDays: 37, Intercalation: 0, BaseWeekday: 1, BaseKanChih: 35, MonthDays: [1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1] },
  { BaseDays: 25, Intercalation: 5, BaseWeekday: 3, BaseKanChih: 41, MonthDays: [1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1] },
  { BaseDays: 44, Intercalation: 0, BaseWeekday: 4, BaseKanChih: 46, MonthDays: [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1] },
  { BaseDays: 33, Intercalation: 0, BaseWeekday: 5, BaseKanChih: 51, MonthDays: [1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 22, Intercalation: 4, BaseWeekday: 6, BaseKanChih: 56, MonthDays: [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0] },
  { BaseDays: 40, Intercalation: 0, BaseWeekday: 1, BaseKanChih: 2, MonthDays: [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0] },
  { BaseDays: 30, Intercalation: 9, BaseWeekday: 2, BaseKanChih: 7, MonthDays: [0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1] },
  { BaseDays: 49, Intercalation: 0, BaseWeekday: 3, BaseKanChih: 12, MonthDays: [0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1] },
  { BaseDays: 38, Intercalation: 0, BaseWeekday: 4, BaseKanChih: 17, MonthDays: [1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0] },
  { BaseDays: 27, Intercalation: 6, BaseWeekday: 6, BaseKanChih: 23, MonthDays: [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1] },
  { BaseDays: 46, Intercalation: 0, BaseWeekday: 0, BaseKanChih: 28, MonthDays: [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0] },
  { BaseDays: 35, Intercalation: 0, BaseWeekday: 1, BaseKanChih: 33, MonthDays: [0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0] },
  { BaseDays: 24, Intercalation: 4, BaseWeekday: 2, BaseKanChih: 38, MonthDays: [0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 42, Intercalation: 0, BaseWeekday: 4, BaseKanChih: 44, MonthDays: [0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1] },
  { BaseDays: 31, Intercalation: 0, BaseWeekday: 5, BaseKanChih: 49, MonthDays: [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0] },
  { BaseDays: 21, Intercalation: 2, BaseWeekday: 6, BaseKanChih: 54, MonthDays: [0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1] },
  { BaseDays: 40, Intercalation: 0, BaseWeekday: 0, BaseKanChih: 59, MonthDays: [0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1] },
  { BaseDays: 28, Intercalation: 6, BaseWeekday: 2, BaseKanChih: 5, MonthDays: [1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0] },
  { BaseDays: 47, Intercalation: 0, BaseWeekday: 3, BaseKanChih: 10, MonthDays: [1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1] },
  { BaseDays: 36, Intercalation: 0, BaseWeekday: 4, BaseKanChih: 15, MonthDays: [1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1] },
  { BaseDays: 25, Intercalation: 5, BaseWeekday: 5, BaseKanChih: 20, MonthDays: [1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0] },
  { BaseDays: 43, Intercalation: 0, BaseWeekday: 0, BaseKanChih: 26, MonthDays: [1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1] },
  { BaseDays: 32, Intercalation: 0, BaseWeekday: 1, BaseKanChih: 31, MonthDays: [1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0] },
  { BaseDays: 22, Intercalation: 3, BaseWeekday: 2, BaseKanChih: 36, MonthDays: [0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0] },
]

const SOLAR_CAL = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
const SOLAR_DAYS = [
  0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365, 396,
  0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366, 397,
]
const ANIMAL_IDX = ["马", "羊", "猴", "鸡", "狗", "猪", "鼠", "牛", "虎", "兔", "龙", "蛇"]
const LOCATION_IDX = ["南.", "東.", "北.", "西."]
const WEEK_NAMES = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]

function getLeap(year: number): number {
  if (year % 400 === 0) return 1
  if (year % 100 === 0) return 0
  if (year % 4 === 0) return 1
  return 0
}

export function getCalConvTitle(): string {
  const today = new Date()
  const solarYear = today.getFullYear()
  const solarMonth = today.getMonth() + 1
  const solarDate = today.getDate()
  const weekday = today.getDay()

  if (solarYear <= FIRST_YEAR || solarYear > LAST_YEAR) {
    return ""
  }

  let sm = solarMonth - 1
  if (sm < 0 || sm > 11) {
    return ""
  }

  let leap = getLeap(solarYear)
  let d: number
  if (sm === 1) {
    d = leap + 28
  } else {
    d = SOLAR_CAL[sm]
  }

  if (solarDate < 1 || solarDate > d) {
    return ""
  }

  let y = solarYear - FIRST_YEAR
  let acc = SOLAR_DAYS[leap * 14 + sm] + solarDate
  const kc = acc + LUNAR_CAL[y].BaseKanChih
  const location = LOCATION_IDX[kc % 4]
  const chih = kc % 12
  const animal = ANIMAL_IDX[chih]

  let lunarYear: number
  if (acc <= LUNAR_CAL[y].BaseDays) {
    y--
    lunarYear = solarYear - 1
    leap = getLeap(lunarYear)
    sm += 12
    acc = SOLAR_DAYS[leap * 14 + sm] + solarDate
  } else {
    lunarYear = solarYear
  }

  let l1 = LUNAR_CAL[y].BaseDays
  let i: number
  for (i = 0; i < 13; i++) {
    const l2 = l1 + LUNAR_CAL[y].MonthDays[i] + 29
    if (acc <= l2) break
    l1 = l2
  }

  let lunarMonth = i + 1
  const lunarDate = acc - l1
  const im = LUNAR_CAL[y].Intercalation
  if (im !== 0 && lunarMonth > im) {
    lunarMonth--
    if (lunarMonth === im) lunarMonth = -im
  }
  if (lunarMonth > 12) lunarMonth -= 12

  const lunarMonthDisplay = lunarMonth < 0 ? "闰" + -lunarMonth : String(lunarMonth)

  return `今:${solarMonth}月${solarDate}日.${WEEK_NAMES[weekday]}.农历:${lunarMonthDisplay}月${lunarDate}日.煞${location} 正冲生肖:${animal}`
}

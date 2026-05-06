import type { PlainRow } from "@/lib/lotteryData"

type RecordRowProps = {
  row: PlainRow
}

export function RecordRow({ row }: RecordRowProps) {
  return (
    <tr>
      <td>
        <span className="blue-text">{row.issue}:</span>
        <span className="black-text">{row.label}</span>
        <span className="zl">【{row.content}】</span>
        <span className="black-text">开:</span>
        {row.result}
      </td>
    </tr>
  )
}

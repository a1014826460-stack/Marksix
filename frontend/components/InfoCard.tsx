import type { InfoSection } from "@/lib/lotteryData"

type InfoCardProps = {
  section: InfoSection
}

export function InfoCard({ section }: InfoCardProps) {
  return (
    <div className="box pad" id={section.anchor ?? section.id}>
      <div className="list-title">{section.title}</div>
      <table border={1} width="100%" className="duilianpt1" cellSpacing={0} cellPadding={2}>
        <tbody>
          {section.rows.map((row) => (
            <tr key={`${section.id}-${row.issue}-${row.label}`}>
              <td>
                <span className="blue-text">{row.issue}:</span>
                <span className="black-text">{row.label}</span>
                <span className="zl">【{row.content}】</span>
                <span className="black-text">开:</span>
                {row.result}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

type NavTabsProps = {
  fixed: boolean
  rows: { label: string; href: string }[][]
}

export function NavTabs({ fixed, rows }: NavTabsProps) {
  return (
    <div className="nav2" data-fixed={fixed ? "fixed" : ""} id="nav2">
      {rows.map((row, rowIndex) => (
        <ul key={`nav-row-${rowIndex}`}>
          {row.map((item) => (
            <li key={item.label}>
              <a href={item.href}>{rowIndex === 0 ? <b>{item.label}</b> : item.label}</a>
            </li>
          ))}
        </ul>
      ))}

      <table className="djck" width="100%" border={0}>
        <tbody>
          <tr>
            <td className="djck1">
              <a href="#7x1m">
                <h2>台湾论坛</h2>
                <p>
                  一码中特 <span>点击查看&gt;</span>
                </p>
              </a>
            </td>
            <td className="djck2">
              <a href="#3t1">
                <h2>台湾资料网</h2>
                <p>
                  三期必开<span>点击查看&gt;</span>
                </p>
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

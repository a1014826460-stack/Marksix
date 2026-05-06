type HeaderProps = {
  currentTime: string
}

export function Header({ currentTime }: HeaderProps) {
  const now = new Date()
  const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]

  return (
    <>
      <div className="box news-box">
        <div className="riqi">
          <b>今:</b>
          <span className="legacy-red">{now.getMonth() + 1}</span>
          <b>月</b>
          <span className="legacy-red">{now.getDate()}</span>
          <b>日.</b>
          <span className="legacy-red">{weekdays[now.getDay()]}.</span>
          <b>农历:</b>
          <span className="legacy-red">四月初五日.</span>
          <b>煞</b>
          <span className="legacy-red">南.</span>
          <b>正冲生肖:</b>
          <span className="legacy-red">马</span>
          <span className="legacy-clock">{currentTime}</span>
        </div>
      </div>

      <div id="fhdb" />
      <div className="box pad" id="yxym">
        <img alt="台湾六合彩论坛头图" src="/vendor/shengshi8800/static/picture/header.jpg" width="100%" />
      </div>
    </>
  )
}

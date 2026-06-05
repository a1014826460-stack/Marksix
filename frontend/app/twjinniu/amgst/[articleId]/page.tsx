import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { getTwjinniuArticleDefinition, getTwjinniuArticleDetail } from "@/lib/twjinniu-articles"

type PageProps = {
  params: Promise<{
    articleId: string
  }>
  searchParams?: Promise<{
    lottery_type?: string
    lotteryType?: string
  }>
}

function ArticleNotice({
  title,
  message,
  isError = false,
}: {
  title: string
  message: string
  isError?: boolean
}) {
  return (
    <div className="box amplIMG" style={{ padding: "0 0 10px" }}>
      <table width="100%" border={1} cellSpacing={0} cellPadding={0}>
        <tbody>
          <tr>
            <td
              className="ymgg-tit2"
              style={{
                backgroundColor: isError ? "#c62828" : "#0c35f5",
                color: "#ffff00",
                fontSize: "16px",
                fontWeight: 700,
                textAlign: "center",
                padding: "6px 4px",
              }}
            >
              {title}
            </td>
          </tr>
          <tr>
            <td
              style={{
                background: isError ? "#fff3f3" : "#fffbe6",
                color: isError ? "#b71c1c" : "#0c35f5",
                textAlign: "center",
                lineHeight: 1.7,
                padding: "10px 8px",
                fontSize: "14px",
                fontWeight: 700,
              }}
            >
              {message}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { articleId } = await params
  const article = getTwjinniuArticleDefinition(articleId)
  const title = article?.title || articleId

  return {
    title: `${title} | 台湾通天网`,
    description: `${title} - 台湾通天网`,
  }
}

export default async function TwjinniuArticlePage({ params, searchParams }: PageProps) {
  const { articleId } = await params
  const resolvedSearchParams = searchParams ? await searchParams : undefined
  const lotteryType =
    Number(resolvedSearchParams?.lottery_type || resolvedSearchParams?.lotteryType || "3") || 3
  const article = await getTwjinniuArticleDetail(articleId, { lotteryType })

  if (!article) {
    notFound()
  }

  return (
    <main style={{ background: "#f5f5f5", minHeight: "100vh", padding: "12px" }}>
      <style>{`
        .twjinniu-article-shell img { max-width: 100%; }
        .twjinniu-article-shell .box img { max-width: 100%; }
        .twjinniu-article-shell .box.img100 img { width: 100%; }
        .twjinniu-article-shell .box table { border-collapse: collapse; }
        .twjinniu-article-shell .box table td { border-collapse: collapse; }
        .twjinniu-article-shell .ymgg table td {
          padding: 0.4em 0;
          border: solid 1px #ccc;
        }
        .twjinniu-article-shell .ymgg table td img {
          vertical-align: middle;
        }
        .twjinniu-article-shell .ymgg-tit1 {
          color: #fff;
          background: #f00;
        }
        .twjinniu-article-shell .ymgg-tit2 {
          color: #ff0;
          background: #00f;
        }
        .twjinniu-article-shell .title {
          padding: 10px 12px 6px;
          text-align: center;
          font-size: 28px;
          font-weight: 700;
          line-height: 1.4;
        }
        .twjinniu-article-shell .topic-author {
          padding: 0 12px 10px;
          text-align: right;
          font-size: 18px;
          line-height: 1.4;
        }
        .twjinniu-article-shell .topic-content {
          padding: 0 14px 12px;
          font-size: 18px;
          line-height: 1.8;
          color: #111;
          word-break: break-word;
        }
        .twjinniu-article-shell .topic-content p {
          margin: 0 0 8px;
        }
        .twjinniu-article-shell .footcp {
          text-align: center;
          padding: 10px 30px 24px;
        }
        .twjinniu-article-shell .footcp * {
          font-size: 15px;
          color: #333;
          line-height: 1.75;
        }
        .twjinniu-article-shell .footcp a {
          height: 1px;
          color: #fff;
          overflow: hidden;
        }
      `}</style>

      <div
        className="twjinniu-article-shell page"
        style={{ border: "1px solid #000", maxWidth: "800px", margin: "0 auto", background: "#fff" }}
      >
        <div className="page-content">
          <div className="box pad" style={{ margin: 0 }}>
            <div className="box amplIMG img100">
              <p>
                <img
                  src="/vendor/twjinniu/static/picture/3b95a6170d2e76d149334c06e21c2c5a.jpg"
                  alt=""
                />
              </p>
            </div>
            <div className="box amplIMG">
              <table width="100%" border={1}>
                <tbody>
                  <tr className="firstRow">
                    <td className="ymgg-tit2" style={{ backgroundColor: "#008000" }}>
                      <p style={{ textAlign: "center" }}>
                        <strong>
                          <span style={{ fontSize: "18px" }}>↓↓↓ 以下网址均可打开资料网 ↓↓↓</span>
                        </strong>
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td align="center">
                      <span style={{ color: "#0000FF" }}>
                        <strong>
                          <span style={{ textDecoration: "none" }}>
                            <span style={{ color: "#000000" }}>
                              <img
                                src="/vendor/twjinniu/static/picture/ffz.gif"
                                alt=""
                                style={{ width: "25px", height: "21px" }}
                              />
                            </span>
                          </span>{" "}
                          <span style={{ textDecoration: "none" }}>
                            <span style={{ color: "#000000", fontSize: "16pt" }}>资料网www.twtongtian.com</span>
                          </span>
                        </strong>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="title">
            <b>
              <span style={{ color: "#FF0000", fontFamily: "Microsoft YaHei" }}>【{article.title}】</span>
              <span style={{ color: "#0000FF" }}>台湾通天网</span>
            </b>
          </div>

          <div className="topic-author">
            <div className="right">
              <div className="name">
                <span style={{ fontSize: "18px" }}>作者:{article.author}</span>
              </div>
            </div>
          </div>

          {article.notes.length ? (
            <ArticleNotice title="资料说明" message={article.notes.join(" ")} isError={article.status === "missing_live_data"} />
          ) : null}

          {article.status === "missing_live_data" ? (
            <ArticleNotice
              title="实时数据状态"
              message={`当前 lottery_type=${article.requestedLotteryType} 的 PostgreSQL 实时数据缺失，页面没有使用旧静态快照冒充最新资料。`}
              isError
            />
          ) : null}

          <div className="topic-content" dangerouslySetInnerHTML={{ __html: article.contentHtml }} />

          <div className="box amplIMG">
            <img src="/vendor/twjinniu/static/picture/sxtu.jpg" alt="" />
          </div>

          <div className="footcp">
            <p>
              <br />
            </p>
            <p>本站声明</p>
            <p>
              柬埔寨六加一六合彩所提供的内容、资料、图片和资讯，只应用在合法的柬埔寨六加一六合彩资料探讨，
              暂不适用于其它外围博彩和非法用途。特此声明！
            </p>
            <p>
              柬埔寨六加一六合彩免责声明：以上所有广告内容均为赞助商提供，本站不对其经营行为负责，
              浏览或使用者须自行承担有关责任，本网站恕不负责。
            </p>
            <p>【柬埔寨六加一】易记域名：www.twtongtian.com</p>
            <p style={{ margin: "0px", height: 0, overflow: "hidden" }}>
              <a href="https://www.tw8800.com/">搭建六合彩开奖论坛</a>
              <a href="https://www.twsaimahui.com/">搭建六合彩图库</a>
              <a href="https://www.twcaibawang.com/">Telegram中文版下载</a>
              <a href="https://www.tw8800.com/">偏门赚钱项目</a>
              <a href="https://www.twsaimahui.com/">搭建六合信用盘</a>
              <a href="https://www.twcaibawang.com/">电报中文版下载</a>
              <a href="https://www.tw8800.com/">Telegram官网下载</a>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}

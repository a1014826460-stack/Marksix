import type { Metadata } from "next"
import { notFound } from "next/navigation"

import { SiteTrafficTracker } from "@/components/SiteTrafficTracker"
import {
  getTwcf888ArticleDefinition,
  getTwcf888ArticleDetail,
  type Twcf888ArticleGroup,
} from "@/lib/twcf888-articles"

export type Twcf888ArticlePageProps = {
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

export async function buildTwcf888ArticleMetadata(articleId: string): Promise<Metadata> {
  const article = getTwcf888ArticleDefinition(articleId)
  const title = article?.title || articleId

  return {
    title: `${title} | 台湾创富网`,
    description: `${title} - 台湾创富网`,
  }
}

export async function renderTwcf888ArticlePage(
  { params, searchParams }: Twcf888ArticlePageProps,
  group: Twcf888ArticleGroup
) {
  const { articleId } = await params
  const resolvedSearchParams = searchParams ? await searchParams : undefined
  const lotteryType =
    Number(resolvedSearchParams?.lottery_type || resolvedSearchParams?.lotteryType || "3") || 3
  const article = await getTwcf888ArticleDetail(articleId, { lotteryType, group })

  if (!article) {
    notFound()
  }

  return (
    <main style={{ background: "#f5f5f5", minHeight: "100vh", padding: "12px" }}>
      <SiteTrafficTracker
        siteKey="twcf888"
        eventType="article_view"
        articleId={articleId}
        path={`/twcf888/${group}/${articleId}`}
      />
      <style>{`
        .twcf888-article-shell img { max-width: 100%; }
        .twcf888-article-shell .box img { max-width: 100%; }
        .twcf888-article-shell .box.img100 img { width: 100%; }
        .twcf888-article-shell .box table { border-collapse: collapse; }
        .twcf888-article-shell .box table td { border-collapse: collapse; }
        .twcf888-article-shell .ymgg-tit1 { color: #fff; background: #f00; }
        .twcf888-article-shell .ymgg-tit2 { color: #ff0; background: #00f; }
        .twcf888-article-shell .title {
          padding: 10px 12px 6px;
          text-align: center;
          font-size: 28px;
          font-weight: 700;
          line-height: 1.4;
        }
        .twcf888-article-shell .topic-author {
          padding: 0 12px 10px;
          text-align: right;
          font-size: 18px;
          line-height: 1.4;
        }
        .twcf888-article-shell .topic-content {
          padding: 0 14px 12px;
          font-size: 18px;
          line-height: 1.8;
          color: #111;
          word-break: break-word;
        }
        .twcf888-article-shell .topic-content p {
          margin: 0 0 8px;
        }
        .twcf888-article-shell .footcp {
          text-align: center;
          padding: 10px 30px 24px;
        }
        .twcf888-article-shell .footcp * {
          font-size: 15px;
          color: #333;
          line-height: 1.75;
        }
      `}</style>

      <div
        className="twcf888-article-shell page"
        style={{ border: "1px solid #000", maxWidth: "800px", margin: "0 auto", background: "#fff" }}
      >
        <div className="page-content">
          <div className="box pad" style={{ margin: 0 }}>
            <div className="box amplIMG img100">
              <p>
                <img
                  src="/vendor/twcf888.com/static/picture/60a842f98b2c538bc635b0533124f08f.png"
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
                          <span style={{ fontSize: "18px" }}>以下网址均可打开资料站</span>
                        </strong>
                      </p>
                    </td>
                  </tr>
                  <tr>
                    <td align="center">
                      <strong>
                        <span style={{ color: "#000000", fontSize: "16pt" }}>
                          资料站 www.twcf888.com
                        </span>
                      </strong>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="title">
            <b>
              <span style={{ color: "#FF0000", fontFamily: "Microsoft YaHei" }}>
                《{article.title}》
              </span>
              <span style={{ color: "#0000FF" }}>台湾创富网</span>
            </b>
          </div>

          <div className="topic-author">
            <span style={{ fontSize: "18px" }}>作者：{article.author}</span>
          </div>

          {article.notes.length ? (
            <ArticleNotice
              title="资料说明"
              message={article.notes.join(" ")}
              isError={article.status === "missing_live_data"}
            />
          ) : null}

          <div className="topic-content" dangerouslySetInnerHTML={{ __html: article.contentHtml }} />

          <div className="box amplIMG">
            <img src="/vendor/twcf888.com/static/picture/sxtu.jpg" alt="" />
          </div>

          <div className="footcp">
            <p>台湾创富网声明</p>
            <p>本站展示内容仅用于站点资料浏览与页面兼容接线演示。</p>
            <p>易记域名：www.twcf888.com</p>
          </div>
        </div>
      </div>
    </main>
  )
}

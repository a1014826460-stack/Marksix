import {
  buildTwcf888ArticleMetadata,
  renderTwcf888ArticlePage,
  type Twcf888ArticlePageProps,
} from "@/components/twcf888/Twcf888ArticlePage"

export async function generateMetadata({ params }: Twcf888ArticlePageProps) {
  const { articleId } = await params
  return buildTwcf888ArticleMetadata(articleId)
}

export default function Twcf888JsbArticlePage(props: Twcf888ArticlePageProps) {
  return renderTwcf888ArticlePage(props, "jsb")
}

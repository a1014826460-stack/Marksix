import { SiteDataPageClient } from "@/components/admin/management-pages"

type SiteDataPageProps = {
  params: Promise<{ id: string }>
}

export default async function SiteDataPage({ params }: SiteDataPageProps) {
  const { id } = await params
  return <SiteDataPageClient siteId={Number(id)} />
}

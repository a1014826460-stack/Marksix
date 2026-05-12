import { SiteDataPage } from "@/features/site-data/SiteDataPage"

type SiteDataPageProps = {
  params: Promise<{ id: string }>
}

export default async function SiteDataPageHandler({ params }: SiteDataPageProps) {
  const { id } = await params
  return <SiteDataPage siteId={Number(id)} />
}

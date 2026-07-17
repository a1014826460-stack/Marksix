import { GET as getArticleDetail } from "@/app/api/sites/[siteKey]/article-detail/route"
import { GET as getHomepageModules } from "@/app/api/sites/[siteKey]/homepage-modules/route"
import { GET as getPredictionModules } from "@/app/api/sites/[siteKey]/prediction-modules/route"
import { GET as getSitePage } from "@/app/api/sites/[siteKey]/site-page/route"
import { POST as postTrafficEvent } from "@/app/api/sites/[siteKey]/traffic-events/route"

type Params = { params: Promise<{ siteKey: string }> }

const request = new Request("http://localhost/api/sites/twjinniu/site-page")
const params: Params = { params: Promise.resolve({ siteKey: "twjinniu" }) }

void getSitePage(request, params)
void getHomepageModules(request, params)
void getPredictionModules(request, params)
void getArticleDetail(request, params)
void postTrafficEvent(request, params)

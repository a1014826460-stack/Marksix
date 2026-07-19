import type { VendorSiteManifest } from "@/lib/site-platform/site-manifest"

export type PublicBridgeConfig = {
  site: {
    site_key: string
    site_id: number
    web_id: number
    lottery_type: 1 | 2 | 3
  }
  api: {
    http_api_base: string
    kaijiang_api_base: string
  }
  bridge: {
    auto_load: {
      draw: boolean
      prediction: boolean
    }
    prediction_module_keys: readonly string[]
  }
  brand: VendorSiteManifest["brand"]
}

export function projectPublicBridgeConfig(manifest: VendorSiteManifest): PublicBridgeConfig {
  return {
    site: {
      site_key: manifest.identity.siteKey,
      site_id: manifest.identity.siteId,
      web_id: manifest.identity.webId,
      lottery_type: manifest.identity.defaultLotteryType,
    },
    api: {
      http_api_base: manifest.bridge.api.httpApiBase,
      kaijiang_api_base: manifest.bridge.api.kaijiangApiBase,
    },
    bridge: {
      auto_load: manifest.bridge.autoLoad,
      prediction_module_keys: manifest.bridge.predictionModuleKeys,
    },
    brand: manifest.brand,
  }
}

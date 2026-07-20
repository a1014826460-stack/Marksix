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
    runtime: {
      draw_selector: string
      prediction_selector: string
      footer_selector: string
      navigation_selector: string
      legacy_prediction_scripts: "disabled" | "enabled"
    }
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
      runtime: {
        draw_selector: manifest.bridge.runtime.drawSelector,
        prediction_selector: manifest.bridge.runtime.predictionSelector,
        footer_selector: manifest.bridge.runtime.footerSelector,
        navigation_selector: manifest.bridge.runtime.navigationSelector,
        legacy_prediction_scripts: manifest.bridge.runtime.legacyPredictionScripts,
      },
    },
    brand: {
      ...manifest.brand,
      footer: {
        ...manifest.brand.footer,
        imageUrls: manifest.brand.footer.imageUrls,
      },
    },
  }
}

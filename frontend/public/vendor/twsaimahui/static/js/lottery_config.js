/**
 * 彩种统一配置
 *
 * 每个彩种独立的 apiBase / web / type 映射。
 * 本地测试 apiBase 指向 Next.js (端口 3000)。
 * 生产环境改回: 'https://admin.shengshi8800.com' / 'https://b.jsc111111.com'
 */
var __legacyLotteryApiBase = (function () {
  function normalizeApiBase(value) {
    if (typeof value !== 'string') {
      return '';
    }
    return value.replace(/\/+$/, '');
  }

  function readApiBaseFromQuery() {
    var search = window.location && typeof window.location.search === 'string'
      ? window.location.search
      : '';
    var match = search.match(/[?&]api_base=([^&]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  return normalizeApiBase(window.__LOTTERY_API_BASE__) ||
    normalizeApiBase(readApiBaseFromQuery()) ||
    '';
})();

window.LOTTERY_CONFIGS = {
  taiwan: {
    label: '台湾彩',
    apiBase: __legacyLotteryApiBase,
    // twsaimahui web_id=6
    web: 6,
    type: 3,
    iframeTabIndex: 0
  },
  macau: {
    label: '澳门彩',
    apiBase: __legacyLotteryApiBase,
    // twsaimahui web_id=6
    web: 6,
    type: 2,
    iframeTabIndex: 1
  },
  hongkong: {
    label: '香港彩',
    apiBase: __legacyLotteryApiBase,
    // twsaimahui web_id=6
    web: 6,
    type: 1,
    iframeTabIndex: 2
  }
};

/** 默认彩种 */
window.DEFAULT_LOTTERY_KEY = 'taiwan';

/** 所有可用的 lotteryKey 列表 */
window.LOTTERY_KEYS = Object.keys(window.LOTTERY_CONFIGS);

function applyLegacyBridgeLotteryConfig(config) {
  if (!config || !config.site || !config.api || !window.LOTTERY_CONFIGS) return;
  var web = Number(config.site.web_id);
  if (!Number.isInteger(web) || web <= 0) return;
  var apiBase = typeof config.api.http_api_base === 'string'
    ? config.api.http_api_base.replace(/\/+$/, '')
    : '';
  Object.keys(window.LOTTERY_CONFIGS).forEach(function (key) {
    window.LOTTERY_CONFIGS[key].web = web;
    window.LOTTERY_CONFIGS[key].apiBase = apiBase;
  });
}

var __legacyBridgeConfig = window.LEGACY_TWSAIMAHUI_RUNTIME && window.LEGACY_TWSAIMAHUI_RUNTIME.bridgeConfig;
applyLegacyBridgeLotteryConfig(__legacyBridgeConfig);
window.addEventListener('lottery:runtime-config-applied', function (event) {
  applyLegacyBridgeLotteryConfig(event && event.detail ? event.detail.config : null);
});

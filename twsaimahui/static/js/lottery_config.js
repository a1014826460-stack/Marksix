/**
 * 彩种统一配置
 *
 * 每个彩种独立的 apiBase / web / type 映射。
 * 注意：web=6 和 type 的值需要后端确认是否为正确映射。
 */
window.LOTTERY_CONFIGS = {
  taiwan: {
    label: '台湾彩',
    apiBase: 'https://admin.shengshi8800.com',
    web: 6,
    type: 3,
    // kj.js 中的 Tab 索引，0=台湾彩, 1=澳门彩, 2=香港彩
    iframeTabIndex: 0
  },
  macau: {
    label: '澳门彩',
    apiBase: 'https://b.jsc111111.com',
    web: 6,
    // 待后端确认：澳门彩的 type 是否确实为 2
    type: 2,
    iframeTabIndex: 1
  },
  hongkong: {
    label: '香港彩',
    apiBase: 'https://admin.shengshi8800.com',
    web: 6,
    // 待后端确认：香港彩的 type 是否确实为 1
    type: 1,
    iframeTabIndex: 2
  }
};

/** 默认彩种 */
window.DEFAULT_LOTTERY_KEY = 'taiwan';

/** 所有可用的 lotteryKey 列表 */
window.LOTTERY_KEYS = Object.keys(window.LOTTERY_CONFIGS);

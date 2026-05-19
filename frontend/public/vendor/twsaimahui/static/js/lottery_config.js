/**
 * 彩种统一配置
 *
 * 每个彩种独立的 apiBase / web / type 映射。
 * 本地测试 apiBase 指向 Next.js (端口 3000)。
 * 生产环境改回: 'https://admin.shengshi8800.com' / 'https://b.jsc111111.com'
 */
window.LOTTERY_CONFIGS = {
  taiwan: {
    label: '台湾彩',
    apiBase: 'http://127.0.0.1:3000',
    // twsaimahui web_id=6
    web: 6,
    type: 3,
    iframeTabIndex: 0
  },
  macau: {
    label: '澳门彩',
    apiBase: 'http://127.0.0.1:3000',
    // twsaimahui web_id=6
    web: 6,
    type: 2,
    iframeTabIndex: 1
  },
  hongkong: {
    label: '香港彩',
    apiBase: 'http://127.0.0.1:3000',
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

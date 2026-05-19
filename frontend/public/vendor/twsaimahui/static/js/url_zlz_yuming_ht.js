// 仅在未通过 lottery_config 初始化时设置默认值
var httpApi = (function () {
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

  return normalizeApiBase(window.httpApi) ||
    normalizeApiBase(window.__LOTTERY_API_BASE__) ||
    normalizeApiBase(readApiBaseFromQuery()) ||
    '';
})();

window.httpApi = httpApi;

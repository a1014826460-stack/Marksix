/**
 * 统一请求工具
 *
 * 基于 jQuery.ajax 的轻量封装，确保所有请求使用当前全局 httpApi/web/type。
 * 后续可逐步将业务模块迁移到此工具。
 */
window.apiClient = {
  /**
   * GET 请求
   * @param {string} url - API 路径，如 '/api/kaijiang/sbzt'
   * @param {object} params - Query 参数对象，会自动合并 web/type
   * @param {object} options - 可选配置 { timeout, headers, ... }
   * @returns {jqXHR}
   */
  get: function (url, params, options) {
    var opts = options || {};
    var runtime = window.LEGACY_TWSAIMAHUI_RUNTIME || null;
    var isKaijiang = runtime && typeof runtime.isKaijiangRequest === 'function' && runtime.isKaijiangRequest(url);
    var finalParams = !isKaijiang && runtime && typeof runtime.withSiteParams === 'function'
      ? runtime.withSiteParams(params)
      : params;
    var requestUrl = isKaijiang
      ? runtime.buildKaijiangUrl(url, params)
      : (window.httpApi || '') + url;
    var request = $.ajax({
      type: 'GET',
      url: requestUrl,
      data: isKaijiang ? undefined : finalParams,
      dataType: 'json',
      timeout: opts.timeout || 10000
    });
    var promise = Promise.resolve(request).then(function (response) {
      return { data: response };
    });
    request.then = promise.then.bind(promise);
    request.catch = promise.catch.bind(promise);
    request.finally = promise.finally ? promise.finally.bind(promise) : undefined;
    return request;
  },

  /**
   * 获取当前全局参数
   * @returns {{ httpApi: string, web: number, type: number }}
   */
  getParams: function () {
    var runtime = window.LEGACY_TWSAIMAHUI_RUNTIME || null;
    return {
      httpApi: window.httpApi,
      web: window.web,
      type: window.type,
      source: runtime && runtime.source ? runtime.source : '',
      domain: runtime && runtime.hostname ? runtime.hostname : ''
    };
  }
};

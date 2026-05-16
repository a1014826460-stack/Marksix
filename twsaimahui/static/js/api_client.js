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
    return $.ajax({
      type: 'GET',
      url: window.httpApi + url,
      data: params,
      dataType: 'json',
      timeout: opts.timeout || 10000
    });
  },

  /**
   * 获取当前全局参数
   * @returns {{ httpApi: string, web: number, type: number }}
   */
  getParams: function () {
    return {
      httpApi: window.httpApi,
      web: window.web,
      type: window.type
    };
  }
};

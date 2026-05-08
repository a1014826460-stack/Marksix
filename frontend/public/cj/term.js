/**
 * 旧站首页会在拿到 curTerm 后再动态加载 `/cj/term.js`。
 *
 * 线上旧环境里这个文件通常负责追加少量页头文案；当前新站隔离壳
 * 只需要保证脚本请求存在，避免 404 HTML 被当成 JS 解析后报
 * `Unexpected token '<'`，从而干扰页面验收。
 */
(function () {
  window.__LEGACY_TERM_SCRIPT_LOADED__ = true;
})();

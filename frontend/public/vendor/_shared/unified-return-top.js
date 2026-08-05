(function (window, document) {
  "use strict";

  function scrollToDocumentTop(event) {
    var target = event.target;
    var link = target && target.closest ? target.closest("a") : null;
    if (!link || !/\u8fd4\u56de\u9876\u90e8/.test(link.textContent || "")) return;
    event.preventDefault();
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }

  document.addEventListener("click", scrollToDocumentTop);
})(window, document);

(function (window, document) {
  "use strict";

  var TITLE_TEXT = "友情链接";

  var styleText = [
    ":host {",
    "  display: block;",
    "}",
    '[data-title] {',
    "  font-size: 18px;",
    "  font-weight: bold;",
    "  text-align: center;",
    "  padding: 8px 0;",
    "  margin-bottom: 10px;",
    "  color: #d32f2f;",
    "  border-bottom: 2px solid #d32f2f;",
    "}",
    '[data-links] {',
    "  display: grid;",
    "  grid-template-columns: repeat(4, 1fr);",
    "  gap: 8px;",
    "}",
    "[data-links] a {",
    "  display: block;",
    "  padding: 6px 8px;",
    "  color: #333;",
    "  text-decoration: none;",
    "  font-size: 14px;",
    "  text-align: center;",
    "  border: 1px solid #e0e0e0;",
    "  border-radius: 4px;",
    "  background: #fff;",
    "}",
    "[data-links] a:hover {",
    "  color: #d32f2f;",
    "  border-color: #d32f2f;",
    "}",
    "@media (max-width: 600px) {",
    "  [data-links] {",
    "    grid-template-columns: repeat(2, 1fr);",
    "  }",
    "}",
  ].join("");

  var templateHTML = [
    "<style>" + styleText + "</style>",
    '<div data-title>' + TITLE_TEXT + "</div>",
    '<div data-links></div>',
  ].join("");

  var ManagedSiteLinks = (function () {
    function ManagedSiteLinks() {
      var self = Reflect.construct(HTMLElement, [], new.target);
      self._fetched = false;
      return self;
    }

    ManagedSiteLinks.prototype = Object.create(HTMLElement.prototype, {
      constructor: { value: ManagedSiteLinks, configurable: true, writable: true },
    });

    ManagedSiteLinks.prototype.connectedCallback = function () {
      var shadow = this.attachShadow({ mode: "open" });
      shadow.innerHTML = templateHTML;
      this._fetchLinks();
    };

    ManagedSiteLinks.prototype._fetchLinks = function () {
      var self = this;
      var siteKey = self.getAttribute("site-key");
      if (!siteKey) return;

      self._fetched = true;

      fetch("/api/site-links?site_key=" + encodeURIComponent(siteKey))
        .then(function (response) {
          if (!response.ok) throw new Error("Request failed with status " + response.status);
          return response.json();
        })
        .then(function (data) {
          self._renderLinks(data.links || []);
        })
        .catch(function () {
          self._clearLinks();
        });
    };

    ManagedSiteLinks.prototype._renderLinks = function (links) {
      var container = this.shadowRoot && this.shadowRoot.querySelector('[data-links]');
      if (!container) return;

      container.replaceChildren();

      for (var i = 0; i < links.length; i++) {
        var link = links[i];
        var a = document.createElement("a");
        a.href = link.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = link.name;
        container.appendChild(a);
      }
    };

    ManagedSiteLinks.prototype._clearLinks = function () {
      var container = this.shadowRoot && this.shadowRoot.querySelector('[data-links]');
      if (container) container.replaceChildren();
    };

    return ManagedSiteLinks;
  })();

  customElements.define("managed-site-links", ManagedSiteLinks);
})(window, document);

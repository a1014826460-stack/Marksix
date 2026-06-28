# Liuhecai Context

This context describes the public lottery site domain language shared by the backend, admin UI, and frontend compatibility layer.

## Language

**Site**:
A public-facing lottery website with its own route, domain identity, visual assets, and default lottery settings.
_Avoid_: Page, project, tenant

**Site Key**:
The stable string identifier used to select a site across configuration, routing, adapters, and API requests.
_Avoid_: Slug, code, web id

**Lottery Type**:
The concrete lottery stream shown by a site, currently Hong Kong, Macau, or Taiwan.
_Avoid_: Game, type, category

**Prediction Module**:
A named forecasting section that shows historical prediction rows and their draw results.
_Avoid_: Widget, block, card

**Article**:
A site content item that may be backed by live prediction data or by preserved vendor assets.
_Avoid_: Post, detail page, snapshot

**Traffic Event**:
A first-party record of a visitor interaction on a public site, such as viewing a site page or opening an article.
_Avoid_: Log line, analytics blob, request record

**Traffic Metrics**:
Aggregated counts derived from traffic events for management reporting, such as page views, visitors, referrers, and site-level trends.
_Avoid_: Dashboard data, raw events

**Canonical Prediction Schema**:
The shared prediction data shape used before data is adapted for a specific site.
_Avoid_: Raw payload, final payload

**Site Adapter**:
A site-specific translator from canonical prediction data into the payload or render model expected by that site.
_Avoid_: Converter, mapper, transformer

**Compatibility Layer**:
The frontend-facing API and routing surface that preserves legacy site behavior while reading from the current backend.
_Avoid_: Backend API, proxy

**Vendor Assets**:
The copied HTML, CSS, JavaScript, images, and fonts that preserve a site's original visual appearance.
_Avoid_: Static app, source site

;(function () {
  var currentScript = document.currentScript
  if (!currentScript || !currentScript.parentNode) return

  function appendText(parent, text) {
    parent.appendChild(document.createTextNode(text))
  }

  function createElement(tagName, attrs, text) {
    var element = document.createElement(tagName)
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        element.setAttribute(key, attrs[key])
      })
    }
    if (typeof text === "string") {
      appendText(element, text)
    }
    return element
  }

  var style = document.createElement("style")
  style.textContent = [
    '.djck { font-family: "Microsoft YaHei"; background: #000; }',
    ".djck td { height: 50px; text-align: center; background: #000; }",
    ".djck td a { text-decoration: none; color: #fff; }",
    ".djck td h2 { font-size: 20px !important; font-weight: bold; margin: 0 !important; padding: 0 !important; }",
    ".djck td p { font-size: 12px; padding-left: 10px; }",
    ".djck td.djck1 h2 { color: #f00; }",
    ".djck td.djck1 p span { color: #FF0; }",
    ".djck td.djck2 h2 { color: #0FF; }",
    ".djck td.djck2 p span { color: #0FF; }",
  ].join("\n")

  var table = createElement("table", {
    class: "djck",
    "data-legacy-brand-static": "djck-static",
    width: "100%",
    border: "0",
  })
  var row = document.createElement("tr")

  function buildCell(className, href, titleText, titleStaticKey, descriptionText) {
    var cell = createElement("td", { class: className })
    var link = createElement("a", { href: href })
    var heading = createElement("h2", { "data-legacy-brand-static": titleStaticKey }, titleText)
    var paragraph = document.createElement("p")
    var span = document.createElement("span")

    appendText(paragraph, descriptionText + " ")
    appendText(span, "点击查看>")
    paragraph.appendChild(span)
    link.appendChild(heading)
    link.appendChild(paragraph)
    cell.appendChild(link)
    return cell
  }

  row.appendChild(buildCell("djck1", "/?t=3", "台湾论坛", "forum-short", "一码中特"))
  row.appendChild(buildCell("djck2", "/?t=3", "台湾资料网", "data-site", "三期必开"))
  table.appendChild(row)

  var parent = currentScript.parentNode
  parent.insertBefore(style, currentScript)
  parent.insertBefore(table, currentScript)
  parent.removeChild(currentScript)
})()

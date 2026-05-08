;(function () {
  var currentScript = document.currentScript
  if (!currentScript || !currentScript.parentNode) return

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

  var wrapper = document.createElement("div")
  wrapper.innerHTML = [
    '<table class="djck" width="100%" border="0">',
    "  <tr>",
    '    <td class="djck1"><a href="http://shengshi8800.com/">',
    "      <h2>台湾论坛</h2>",
    '      <p>一码中特 <span>点击查看&gt;</span></p>',
    "    </a></td>",
    '    <td class="djck2"><a href="http://shengshi8800.com">',
    "      <h2>台湾资料网</h2>",
    '      <p>三期必开 <span>点击查看&gt;</span></p>',
    "    </a></td>",
    "  </tr>",
    "</table>",
  ].join("")

  var parent = currentScript.parentNode
  parent.insertBefore(style, currentScript)
  while (wrapper.firstChild) {
    parent.insertBefore(wrapper.firstChild, currentScript)
  }
  parent.removeChild(currentScript)
})()

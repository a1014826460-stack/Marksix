(function () {
	var KJ_STYLE_ID = "legacy-kj-tab-style";
	var CURRENT_SCRIPT = document.currentScript;
	var KJ_MARKUP = `
<div class="KJ-TabBox">
    <ul>
    <li data-opt="{'color':'#ffffff','url':'/vendor/shengshi8800/kj/local.html?lottery_type=3&label=%E5%8F%B0%E6%B9%BE%E5%BD%A9','height':160}">
    台湾彩
    </li>
    <li data-opt="{'color':'#ffffff','url':'/vendor/shengshi8800/kj/local.html?lottery_type=2&label=%E6%BE%B3%E9%97%A8%E5%BD%A9','height':160}">
    澳门彩
    </li>
    <li data-opt="{'color':'#ffffff','url':'/vendor/shengshi8800/kj/local.html?lottery_type=1&label=%E9%A6%99%E6%B8%AF%E5%BD%A9','height':160}">
    香港六合彩
    </li>
    </ul>
    <div></div>
    <div></div>
    <div></div>
</div>

<div class="waibox">
<a class="location_to" href="/vendor/shengshi8800/index.html" target="_blank">点击进入台湾彩报码直播开奖</a>
</div>
`;
	var KJ_STYLE = `
.KJ-TabBox { min-height: 226px; height: auto; overflow: visible; color:#333; background: #fff; font-family: 'PingFang SC', 'microsoft yahei', arial, 'helvetica neue', 'hiragino sans gb', sans-serif;}
.KJ-TabBox ul,.KJ-TabBox li{margin:0;list-style:none;padding:0;border:0;font-size: 18px;}
.KJ-TabBox ul { display: flex; height: 36px; padding: 8px 0 0 8px; box-sizing: border-box; border-bottom: solid 2px #FFF;}
.KJ-TabBox li{ flex: 1; height: 26px; line-height: 26px; margin-right: 8px; text-align: center; border-radius: 4px; background: #eee; cursor: pointer;}
.KJ-TabBox li.cur{ color: #fff; background: #FF9900;}
.KJ-TabBox li:nth-child(1).cur { background: #1FB61D;}
.KJ-TabBox li:nth-child(2).cur { background: #E71607;}
.KJ-TabBox li:nth-child(3).cur { background: #2389E9;}
.KJ-TabBox li:nth-child(4).cur { background: #B907C1;}
.KJ-TabBox div{display:none;}
.KJ-TabBox div.cur{display:block!important;}
.KJ-TabBox .KJ-IFRAME{}
@media screen and (max-width: 650px) {
.KJ-TabBox ul,.KJ-TabBox li { font-size: 16px;}
}
.waibox {text-align: center;background: linear-gradient(to top,#9C27B0,#673AB7);line-height: 55px;margin: 1px 0 0;padding: 0;list-style-type: none;border: none;clear: both;}
.waibox a:link {text-decoration: none;}
.waibox .location_to {padding: 8px 10px;background: beige;border-radius: 15px;color: #f44336;font-weight: 700;letter-spacing: 1px;box-shadow: 2px 2px 1px #f44336;}
`;

	function ensureStyle() {
		if (document.getElementById(KJ_STYLE_ID)) return;
		var styleEl = document.createElement("style");
		styleEl.id = KJ_STYLE_ID;
		styleEl.textContent = KJ_STYLE;
		document.head.appendChild(styleEl);
	}

	function renderKjMarkup() {
		var mount = CURRENT_SCRIPT && CURRENT_SCRIPT.parentNode ? CURRENT_SCRIPT.parentNode : null;
		if (!mount) return null;
		mount.innerHTML = KJ_MARKUP;
		return mount;
	}

	ensureStyle();
	renderKjMarkup();

	var KJTB ={
		$(str){return document.querySelector(str);},
		resolveInitialType(){
			try{
				if(window.__LEGACY_GAME_STATE__ && typeof window.__LEGACY_GAME_STATE__.getType === "function"){
					return Number(window.__LEGACY_GAME_STATE__.getType()) || 3;
				}
			}catch(e){}
			return 3;
		},
		resolveTabType(el){
			var data = el && el.getAttribute ? el.getAttribute("data-opt") : "";
			if(!data) return 3;
			try{
				var opt = JSON.parse(data.replace(/'/g,"\""));
				var url = String(opt && opt.url ? opt.url : "");
				var match = url.match(/[?&]lottery_type=(\d+)/);
				if(match) return Number(match[1]) || 3;
			}catch(e){}
			return 3;
		},
		init(str){
			var that = this;
			var dom = this.$(str);
			if(!dom) return;
			dom.addEventListener("click",function(e){
				var el = e.target;
				if(el.tagName != "LI"||el.className=="cur")return;
				var ind = Math.floor(that.index(el)/2);
				var nodes = dom.querySelectorAll("li");
				for(var item of nodes){
					item.removeAttribute("style");
					item.removeAttribute("class");
				}
				el.className="cur";
				nodes = dom.querySelectorAll("div");
				for(var divItem of nodes){
					if(divItem.getAttribute("class")=="cur") that.leave(divItem);
					divItem.removeAttribute("style");
					divItem.removeAttribute("class");
				}
				var node = that.getEl(dom,ind,"DIV");
				node.className="cur";
				that.cur(dom,el,node);
			});
			var initialType = that.resolveInitialType();
			var tabs = dom.querySelectorAll("li");
			var node = null;
			for(var i = 0; i < tabs.length; i++){
				if(that.resolveTabType(tabs[i]) === initialType){
					node = tabs[i];
					break;
				}
			}
			if (!node) node = that.getEl(dom.querySelector("UL"),0,"LI");
			if (node) node.click();
			[[document,"DOMContentLoaded"],[window,"resize"]].forEach((item)=>{
				var removeEl=(id)=>{
					try{
						var ifr = document.getElementById(id);
						ifr.parentNode.removeChild(ifr);
					}catch(e){}
				};
				var insert = (id,str)=>{
					var styleDom = document.createElement("style");
					styleDom.id = id;
					styleDom.innerHTML = str;
					document.head.appendChild(styleDom);
				};
				item[0].addEventListener(item[1],function(){
					removeEl("kj-iframe-css");
					var w = window.screen.availWidth;
					if(w<=650 && w>500){
						insert("kj-iframe-css",".KJ-IFRAME{height:200px;}");
					}else if(w<=500 && w>450){
						insert("kj-iframe-css",".KJ-IFRAME{height:200px;}");
					}else if(w<=450 && w>350){
						insert("kj-iframe-css",".KJ-IFRAME{height:210px;}");
					}else if(w<=350){
						insert("kj-iframe-css",".KJ-IFRAME{height:220px;}");
					}
				},false);
			});
		},
		cur(dom,el,node){
			var data = el.getAttribute("data-opt");
			data = JSON.parse(data.replace(/'/g,"\""));
			el.style.color = data.color;
			el.style.borderColor = data.color;
			node.style.borderColor = data.color;

			var tid = node.getAttribute("_tid");
			if(tid){
				clearTimeout(parseInt(tid, 10));
				node.removeAttribute("_tid");
				return;
			}
			node.innerHTML = `
				<iframe class="KJ-IFRAME" src="${data.url}" width="100%" height="${data.height}" frameborder="0" scrolling="no"></iframe>
			`;
		},
		leave(item){
			function remove(el){
				this.id = setTimeout(()=>{
					if(!el.getAttribute("_tid")) return;
					el.removeAttribute("_tid");
					el.innerHTML="";
				},1000*10);
				el.setAttribute("_tid",this.id);
			}
			new remove(item);
		},
		index(el,tag){
			var node = el.parentNode.childNodes;
			var index = -1;
			for(var item of node){
				(tag) ? (tag==item.tagName) && index++ : index++;
				if (item===el) return index;
			}
			return index;
		},
		getEl(el,index,tag){
			var i = -1;
			for(var item of el.childNodes){
				(tag) ? (tag==item.tagName) && i++ : i++;
				if(index==i) return item;
			}
		}
	};
	KJTB.init(".KJ-TabBox");
})();

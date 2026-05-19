document.write(`
<style>
.KJ-TabBox { height: 166px; overflow: visible; color:#333; background: #fff; font-family: 'PingFang SC', 'microsoft yahei', arial, 'helvetica neue', 'hiragino sans gb', sans-serif;}
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
</style>
<div class="KJ-TabBox">
    <ul>
    <li data-opt="{'color':'#ffffff','url':'/vendor/twsaimahui/kj/local.html?lottery_type=3&label=台湾彩','height':220}">
    台湾彩
    </li>
    <li data-opt="{'color':'#ffffff','url':'/vendor/twsaimahui/kj/local.html?lottery_type=2&label=澳门彩','height':220}">
    澳门彩
    </li>
    <li data-opt="{'color':'#ffffff','url':'/vendor/twsaimahui/kj/local.html?lottery_type=1&label=香港彩','height':220}">
    香港彩
    </li>
    

    </ul>
    <div></div>
    <div></div>
    <div></div>
    <div></div>
</div>
	<div class="waibox">
	<style>
	.waibox {text-align: center;background: linear-gradient(to top,#9C27B0,#673AB7);line-height: 55px;margin: 0;padding: 0;list-style-type: none;border: none;}
	.waibox a:link {text-decoration: none;}
	.waibox .location_to {padding: 10px;background: beige;border-radius: 15px;color: #f44336;font-weight: 700;letter-spacing: 1px;box-shadow: 2px 2px 1px #f44336;}
	</style>
	<a class="location_to" href="http:///00853.html" target="_blank"><img src="https://d31q194n7fpdes.cloudfront.net/mygai/tp/images/hands.gif" style="vertical-align: middle;width:45px;">台湾赛马会永久网站www.twsaimahui.com</a>
	</div>

`);

var KJTB ={
	$(str){return document.querySelector(str);},
	resolveTabType(el){
		if(!el) return null;
		var data = el.getAttribute('data-opt');
		if(!data) return null;
		try{
			data = JSON.parse(data.replace(/'/g,"\""));
			var url = String(data.url || "");
			var match = url.match(/[?&]lottery_type=(\d+)/);
			return match ? Number(match[1]) : null;
		}catch(err){
			console.warn('[twsaimahui] resolveTabType parse failed', err);
			return null;
		}
	},
	resolveLotteryKey(el){
		var type = this.resolveTabType(el);
		var keyMap = {
			3: "taiwan",
			2: "macau",
			1: "hongkong"
		};
		return keyMap[type] || null;
	},
	getCurrentLotteryKey(){
		return (
			(window.appState && window.appState.lotteryKey) ||
			localStorage.getItem("selectedLottery") ||
			window.DEFAULT_LOTTERY_KEY ||
			"taiwan"
		);
	},
	activate(dom,el){
		if(!dom || !el) return;
		var ind = Math.floor(this.index(el)/2);
		var nodes = dom.querySelectorAll("li");
		for(var item of nodes){
			item.removeAttribute("style");
			item.removeAttribute("class");
		}
		el.className="cur";
		nodes = dom.querySelectorAll("div");
		for(var item of nodes){
			if(item.getAttribute("class")=="cur") this.leave(item);
			item.removeAttribute("style");
			item.removeAttribute("class");
		}
		var node = this.getEl(dom,ind,"DIV");
		if(!node) return;
		node.className="cur";
		this.cur(dom,el,node);
	},
	activateByLotteryKey(lotteryKey){
		var tabMap = { taiwan: 0, macau: 1, hongkong: 2 };
		var idx = tabMap[lotteryKey];
		if (idx === undefined) return;
		var dom = document.querySelector('.KJ-TabBox');
		if (!dom) return;
		var li = this.getEl(dom.querySelector("UL"), idx, "LI");
		if (!li) return;
		dom.setAttribute("data-kj-sync-disabled","1");
		try{
			this.activate(dom,li);
		}finally{
			dom.removeAttribute("data-kj-sync-disabled");
		}
	},
		init(str){
			var that = this;
			var dom = this.$(str);
			if(!dom) return;
			dom.addEventListener("click",function(e){
				var el = e.target;
				if(el.tagName != "LI"||el.className=="cur")return;
				var type = that.resolveTabType(el);
				var lotteryKey = that.resolveLotteryKey(el);
				console.log('[twsaimahui] kj tab click', {
					label: el.textContent && el.textContent.trim(),
					type: type,
					lotteryKey: lotteryKey,
					currentLotteryKey: window.appState && window.appState.lotteryKey
				});

				if(
					!dom.getAttribute("data-kj-sync-disabled") &&
					lotteryKey &&
					window.appState &&
					window.appState.lotteryKey !== lotteryKey &&
					typeof window.switchLottery === "function"
				){
					console.log('[twsaimahui] kj tab sync switchLottery', {
						lotteryKey: lotteryKey,
						type: type
					});
					window.switchLottery(lotteryKey);
					return;
				}

				that.activate(dom,el);
		});
		var initialKey = that.getCurrentLotteryKey();
		var initialTypeKeyMap = { taiwan: 0, macau: 1, hongkong: 2 };
		var initialLi = that.getEl(dom.querySelector("UL"), initialTypeKeyMap[initialKey] || 0, "LI");
		if(initialLi) that.activate(dom,initialLi);
		[[document,"DOMContentLoaded"],[window,"resize"]].forEach((item,index,self)=>{
			var removeEl=(id)=>{
				try{
					var ifr = document.getElementById(id);
					ifr.parentNode.removeChild(ifr);
				}catch(e){}
			};
			var insert = (id,str)=>{
				var dom = document.createElement("style");
				dom.id = id;
				dom.innerHTML = str;
				document.head.appendChild(dom);			
			}
			item[0].addEventListener(item[1],function(){
				removeEl("kj-iframe-css");
				var w = window.screen.availWidth;
				if(w<=650 && w>500){
					insert("kj-iframe-css",".KJ-IFRAME{height:170px;}");
				}else if(w<=500 && w>450){
					insert("kj-iframe-css",".KJ-IFRAME{height:150px;}");
				}else if(w<=450 && w>350){
					insert("kj-iframe-css",".KJ-IFRAME{height:140px;}");
				}else if(w<=350){
					insert("kj-iframe-css",".KJ-IFRAME{height:190px;}");
				}
			},false);
		});
	},
	cur(dom,el,node){
		var that = this;
		var data = el.getAttribute('data-opt');
		data = JSON.parse(data.replace(/'/g,"\""));
		el.style.color = data["color"];
		el.style.borderColor = data["color"];
		node.style.borderColor = data["color"];

		var tid = node.getAttribute("_tid");
		if(tid){
			clearTimeout(parseInt(tid));
			node.removeAttribute("_tid");
			return;
		}
		node.innerHTML = `
			<iframe class="KJ-IFRAME" src="${data["url"]}" width="100%" height="${data["height"]}" frameborder="0" scrolling="no"></iframe>
		`;
	},
	leave(item){
		var that = this;
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

/**
 * 根据 lotteryKey 切换开奖 iframe Tab
 * 供 index.html 中的 switchLottery() 调用
 * @param {string} lotteryKey - 'taiwan' | 'macau' | 'hongkong'
 */
	window.updateKjIframe = function(lotteryKey) {
		console.log('[twsaimahui] updateKjIframe', lotteryKey);
    KJTB.activateByLotteryKey(lotteryKey);
};

//波色  "蓝波,红波"
function bose2(str,attach,spStr){
	let ql = str.split(',')
	let sg = ''
	let ret = ''
	if( null == spStr || spStr.length == 0 || undefined == attach || Object.keys(attach).length == 0){

		return ql.join('+')
	}
	let sx_ = spStr.split(',');
	let sx = zhuanzi(sx_[sx_.length -1])

	for(let i in ql){
		attach.forEach(itm=>{
			if( ql[i] == itm.name){
				sg = ql[i]
				ret += ret.length>0?`+`:''
				if(itm.code.indexOf(sx) != -1){
					ret += `<span style="background-color: #FFFF00">${sg}</span>`
				}else{
					ret +=  sg
				}
			}
		})
	}
	return ret;
}

//三国
function sanguo(str,attach,spStr){
	let ql = JSON.parse(str)
	let sg = ''
	let ret = ''
	if( null == spStr || spStr.length == 0 || undefined == attach || Object.keys(attach).length == 0){

		ql.forEach(el => {
			ret += el.split('|')[0]
		});
		return ret
	}
	let sx_ = spStr.split(',');
	let sx = zhuanzi(sx_[sx_.length -1])

	for(let i in ql){
		attach.forEach(itm=>{
			if( ql[i].indexOf(itm.name) != -1){
				sg = ql[i].split('|')[0].replace('国','')
				if(itm.code.indexOf(sx) != -1){
					ret += `<span style="background-color: #FFFF00">${sg}</span>`
				}else{
					ret += sg
				}
			}
		})
	}
	return ret;
}

//五行 str是json 数组
function wuxing(str,spStr){
	let ql = JSON.parse(str)
	let wx = ''
	let ret = ''
	if( null == spStr || spStr.length == 0 ){
		ql.forEach(el => {
			ret += el.split('|')[0]
		});
		return ret
	}
	let sx_ = spStr.split(',');
	let sx = zhuanzi(sx_[sx_.length -1])
	ql.forEach(el => 
	{
		wx = el.split('|')[0]
		if(el.indexOf(sx) != -1){
			ret += `<span style="background-color: #FFFF00">${wx}</span>`
		}else{
			ret += wx
		}
					
		
	});
	
	return ret;
}

//琴棋书画
function qqsh(str,attach,spStr){
	if(undefined == str || str.length == 0){
		return '';
	}
	if( null == spStr || spStr.length == 0 || undefined == attach || Object.keys(attach).length == 0){
		return str.replaceAll(',','');
	}
	let sx_ = spStr.split(',');
	let sx = zhuanzi(sx_[sx_.length -1])
	let ql = str.split(',')
	let ret = ''
	for(let i in ql){
		attach.forEach(itm=>{
			if(itm.name == ql[i]){
				if(itm.code.indexOf(sx) != -1){
					ret += `<span style="background-color: #FFFF00">${ql[i]}</span>`
				}else{
					ret += ql[i]
				}
			}
		})
	}
	return ret;
}

//选中码
function xuanzhongCodeSxsm(yuceStr,kaijiangStr){
    let yuceArr = yuceStr.split(',');
    let newArr = []
    let index = 0
    if(kaijiangStr){
        let kaijiangArr = kaijiangStr.split(',');
        for(let i in yuceArr){
            newArr[i] = yuceArr[i]
            //for(let j in kaijiangArr){
                if(yuceArr[i] == kaijiangArr[kaijiangArr.length-1]){
                    newArr[i] = `<span style="background-color: #FFFF00">${yuceArr[i]}</span>`
                    index = i
                }
           //}
        }
    }else{
       newArr =  yuceArr
    }
    //console.log(newArr)
    return {ma:yuceArr,index:index}
    
}

function replaceLast(str, search, replacement) {
  const lastIndex = str.lastIndexOf(search);
  if (lastIndex === -1) {
    return str;
  }
  return str.substring(0, lastIndex) + replacement + str.substring(lastIndex + search.length);
}

function matchFromEnd(str, charToMatch) {
  const regex = new RegExp(charToMatch + '$');
  return regex.test(str);
}

function zhuanzi(str) {
  let ss = str 
 if(str == '龍'){
    ss = '龙' 
 }
 
 if(str == '馬'){
    ss = '马' 
 }
 
 if(str == '雞' || str == '鷄' ){
    ss = '鸡' 
 }
 
 if(str == '豬'){
    ss = '猪' 
 }
  
  return ss;
}


//选中字
function xuanzhongStr(str,kaijiangStrSx){
	
    if(kaijiangStrSx){
        let kaijiangArr = kaijiangStrSx.split(',');
        for(let i in kaijiangArr){
            
            let sx = zhuanzi(kaijiangArr[i])
            
            if( matchFromEnd(str, sx) ){
                //str = replaceLast(str, kaijiangArr[i], `<span style="background-color: #FFFF00">${kaijiangArr[i]}</span>`)
                let newStr = `<span style="background-color: #FFFF00">${sx}</span>`
	                str = replaceLast(str, sx, newStr)
            }
 
        }
    }
    
    return str
    
}


function xuanzhongCodejxjm(yuceStr,kaijiangStr){
    let yuceArr = yuceStr.split(',');
    let newArr = []
    if(kaijiangStr){
        let kaijiangArr = kaijiangStr.split(',');
        for(let i in yuceArr){
            newArr[i] = yuceArr[i]
            //for(let j in kaijiangArr){
                if( yuceArr[i] == zhuanzi(kaijiangArr[kaijiangArr.length-1]) ){
                    newArr[i] = `<span style="background-color: #FFFF00">${yuceArr[i]}</span>`
                }
           //}
        }
    }else{
       newArr =  yuceArr
    }
    //console.log(newArr)
    return newArr
    
}

//替换字符串
function replaceAll(str, find, replace) {
  return str.replace(new RegExp(find, 'g'), replace);
}


function xuanzhongStrPhct(str,kaijiangStrSx){
	let index=0;
    if(kaijiangStrSx){
        let kaijiangArr = kaijiangStrSx.split(',');
        for(let i in kaijiangArr){
            
            let sx = zhuanzi(kaijiangArr[i])
            
            if( matchFromEnd(str, sx) ){
                //str = replaceLast(str, kaijiangArr[i], `<span style="background-color: #FFFF00">${kaijiangArr[i]}</span>`)
                let newStr = `<span style="background-color: #FFFF00">${sx}</span>`
	            str = replaceLast(str, sx, newStr)
	            index=i
            }
 
        }
    }
    
    return {str:str,index: parseInt(index) }
    
}


//10码中特
function xuanzhongCodeSem(yuceStr,kaijiangStr){
    let yuceArr = yuceStr.split(',');
    let newArr = []
    let index = 0
    if(kaijiangStr){
        let kaijiangArr = kaijiangStr.split(',');
        for(let i in yuceArr){
            newArr[i] = yuceArr[i]
            //for(let j in kaijiangArr){中特取最后一个
                if(yuceArr[i] == kaijiangArr[kaijiangArr.length-1]){
                    newArr[i] = `<span style="background-color: #FFFF00">${yuceArr[i]}</span>`
                    if(index==0 && i<kaijiangArr.length) index = i
               }
          //  }
        }
    }else{
       newArr =  yuceArr
    }
    //console.log(newArr)
    return { maArr:newArr,index:index}
    
}


//平特藏宝 选中
function selTxtPt(sp,str){
    
    let resStr = "";
    let arr = sp.split('.');
    let spArr = arr[arr.length-1].split('T');
    let spStr = spArr[spArr.length-1];
    let strArr = str.split('.');
    strArr.forEach((el,index)=>{
        
        if(el == zhuanzi(spStr)){
            resStr += `<span style="background-color: #FFFF00">${el}</span>`;
        }else{
            resStr += el;
        }
        if(index != strArr.length-1){
             resStr += ".";
        }
        
    })
    
    
    return resStr;
}

//4肖 选中
function selTxtBc(str,spStr){
    
    if (null == spStr || spStr.length <= 0){
        
        return str;
    }else{
        let resStr = "";
		let spArr = spStr.split(",")
        let sp = spArr[spArr.length-1];
    
        for(let i = 0 ; i < str.length ; i++){
            if(str[i] == zhuanzi(sp)){
                resStr += `<span style="background-color: #FFFF00">${str[i]}</span>`;
            }else{
                resStr += str[i];
            }
        }
        
        return resStr;
    }
}

//四季 [\"春\",\"冬\",\"夏\"
function parseSjsx(content,ori,res_sx){
	if(null == content || ori.length == 0 ){
		return '';
	}
	cnt = JSON.parse(content);
	let ori_  = '';
	let ret = '';
	let is_exist = false;
	let sx = res_sx.split(',')
	for(let i = 0; i<cnt.length;i++){
		ori_ = '';
		is_exist = false;
		ori_ = ori.filter(item=>{
			return item.name.indexOf(cnt[i]) != -1
		})
		if(ori_.length >0){
			let ori_s = ori_[0].code.split(',');
			ori_s.forEach(itm=>{
				if(res_sx[res_sx.length -1] == itm ){
					is_exist = true
				}
			});
		}
		if(is_exist){
			ret += `<span style="background-color: #FFFF00">${cnt[i]}</span>`;
		}else{
			ret += cnt[i]
		}
	}
	return ret;
}
//四季 [\"冬肖|猪,牛,鼠\",\"春肖|兔,虎,龙\",\"夏肖|羊,蛇,马\"]
function parseSjsx2(content,res_sx){
	if(null == content ){
		return '';
	}
	let sj  = '';
	let ret = '';
	let cnt = JSON.parse(content);
	if(res_sx ==null ||res_sx.length==0){
		for(let i in cnt){
			sj = cnt[i].substr(0,1)

			ret += sj
		
		}
		return ret;
	}

	let is_exist = false;
	let sx = res_sx.split(',')
	let tx = sx[sx.length -1]
	for(let i in cnt){
		is_exist = false
		sx.forEach(itm=>{
			if( cnt[i].indexOf(tx) != -1){
				is_exist = true
			}
		})
		sj = cnt[i].substr(0,1)
		if(is_exist){
			ret += `<span style="background-color: #FFFF00">${sj}</span>`;
		}else{
			ret += sj
		}
	}
	return ret

}
//stqw 选中
function selTxtBcT(str,spStr){
    
    if (null == spStr || spStr.length <= 0){
        
        return str;
    }else{
        let resStr = "";
		
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		
		let strArr = str.split("-");
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == sp[0]){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
            }else{
                resStr += strArr[i];
            }
			if(i != strArr.length-1){
			     resStr += "-";
			}
        }
        
        return resStr;
    }
}
//头 0-3-2
function selTxtBcT2(str,spStr){
    
    if (null == spStr || spStr.length <= 0){
        
        return str+'头';
    }else{
        let resStr = "";
		
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		
		let strArr = str.split("-");
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == sp[0]){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}头</span>`;
            }else{
                resStr += strArr[i]+'头';
            }
			if(i != strArr.length-1){
			     resStr += "-";
			}
        }
        
        return resStr;
    }
}

//头 ["0头|01,02,03,04,05,06,07,08,09","2头|20,21,22,23,24,25,26,27,28,29","3头|30,31,32,33,34,35,36,37,38,39"]
function selTxtBcT3(str,spStr){
    if(null == str || str.length == 0){
		return ;
	}
	let yc = JSON.parse(str)
	let resStr = "";
    if (null == spStr || spStr.length <= 0){
        yc.forEach(el => {
			resStr += resStr.length>0?',':''
			resStr += el.split('|')[0]
		});
        return resStr;
    }else{
		
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		let t = ''
		let strArr = str.split("-");
        for(let i = 0 ; i < yc.length ; i++){
			t = yc[i][0]
			resStr += resStr.length>0?',':''
            if(t == sp[0]){
                resStr += `<span style="background-color: #FFFF00">${t}头</span>`;
            }else{
                resStr += t+'头';
            }
		
        }
        
        return resStr;
    }
}

//头 ["6尾|06,16,26,36,46","0尾|10,20,30,40","5尾|05,15,25,35,45","3尾|03,13,23,33,43","1尾|01,11,21,31,41","8尾|08,18,28,38,48"]
function selTxtBcW3(str,spStr){
    if(null == str || str.length == 0){
		return ;
	}
	let yc = JSON.parse(str)
	let resStr = "";
    if (null == spStr || spStr.length <= 0){
        yc.forEach(el => {
			resStr += resStr.length>0?',':''
			resStr += el.split('|')[0]
		});
        return resStr;
    }else{
		
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		let t = ''
		let strArr = str.split("-");
        for(let i = 0 ; i < yc.length ; i++){
			t = yc[i][0]
			resStr += resStr.length>0?',':''
            if(t == sp[sp.length-1]){
                resStr += `<span style="background-color: #FFFF00">${t}尾</span>`;
            }else{
                resStr += t+'尾';
            }
		
        }
        
        return resStr;
    }
}

//stqw 选中
function selTxtBcW(str,spStr){
    
    let resStr = "";
    
    if (null == spStr || spStr.length <= 0){
        let strArr = str.split("-");
        strArr.forEach((el,index)=>{
            
            resStr += strArr[index];
            if(index != zhuanzi(strArr.length-1)){
        	     resStr += ".";
        	}
        })
        
        
        return resStr;
    }else{
        let spArr = spStr.split(",");
        let sp = spArr[spArr.length-1];
        
        let strArr = str.split("-");
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == sp[sp.length-1]){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
            }else{
                resStr += strArr[i];
            }
        	if(i != strArr.length-1){
        	     resStr += ".";
        	}
        }
        
        return resStr;
    }
}
//stqw 选中
function selTxtBcW2(str,spStr){
    
    let resStr = "";
    
    if (null == spStr || spStr.length <= 0){
        let strArr = str.split("-");
        strArr.forEach((el,index)=>{
            
            resStr += strArr[index]+'尾';
            if(index != zhuanzi(strArr.length-1)){
        	     resStr += ".";
        	}
        })
        
        
        return resStr;
    }else{
        let spArr = spStr.split(",");
        let sp = spArr[spArr.length-1];
        
        let strArr = str.split("-");
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == sp[sp.length-1]){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}尾</span>`;
            }else{
                resStr += strArr[i]+'尾';
            }
        	if(i != strArr.length-1){
        	     resStr += ".";
        	}
        }
        
        return resStr;
    }
}
// 选出
function selNumBcMaArr(str,spStr){
    
	let resStr = "";
	let strArr = str.split(",");
    if (null == spStr || spStr.length <= 0){

        return resStr;
    }else{
		let spArr = spStr.split(",")
        let sp = spArr[spArr.length-1];
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == zhuanzi(sp)){
				resStr += strArr[i]+',';
            }
        }
        
        return resStr.substring(0,resStr.length -1);
    }
}

// bxjym 选中
function selNumBc(str,spStr){
    
    if (null == spStr || spStr.length <= 0){
        
        return str;
    }else{
        let resStr = "";
		let spArr = spStr.split(",")
        let sp = spArr[spArr.length-1];
        let strArr = str.split(".");
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == zhuanzi(sp)){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
            }else{
                resStr += strArr[i];
            }
        	if(i != strArr.length-1){
        	     resStr += ".";
        	}
        }
        
        return resStr;
    }
}


// ma22 选中
function selNumBcMa22(str,spStr){
    
	let resStr = "";
	let strArr = str.split(",");
    if (null == spStr || spStr.length <= 0){
		for(let i = 0 ; i < strArr.length ; i++){
		    resStr += strArr[i];
		}
        return resStr;
    }else{
		let spArr = spStr.split(",")
        let sp = spArr[spArr.length-1];
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == zhuanzi(sp)){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
            }else{
                resStr += strArr[i];
            }
        }
        
        return resStr;
    }
}

// jrxq 选中
function selNumBcJrxq(str,spStr){
    let resStr = "";
	let strArr = str.split(",");
	
    if (null == spStr || spStr.length <= 0){
        
		for(let i = 0 ; i < strArr.length ; i++){
		    resStr += strArr[i];
			if(i != strArr.length-1){
			     resStr += ".";
			}
		}
		
        return resStr;
    }else{
        
		let spArr = spStr.split(",")
        let sp = spArr[spArr.length-1];
        
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == zhuanzi(sp)){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
            }else{
                resStr += strArr[i];
            }
        	if(i != strArr.length-1){
        	     resStr += ".";
        	}
        }
        
        return resStr;
    }
}
// dwss 选中
function selNumBcDwss(str,spStr){

	
    if (null == spStr || spStr.length <= 0){
        
        return str;
    }else{
        
		let resStr = str.substring(0,str.length-5);
		let strArr = str.substring(str.length-5,str.length-1);
		
		let spArr = spStr.split(",");
        let sp = spArr[spArr.length-1];
        
        for(let i = 0 ; i < strArr.length ; i++){
            if(strArr[i] == sp[0]){
                resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
            }else{
                resStr += strArr[i];
            }
        }
        resStr += str[str.length-1];
		
        return resStr;
    }
}



function getResult(codeStr,zodiacStr){
    
    
    if(null != codeStr && null != zodiacStr && codeStr.length > 0 && zodiacStr.length >0){
        let resStr = "";
        let codeArr = codeStr.split(",");
        let zodiacArr = zodiacStr.split(",");
        
        
        return zodiacArr[zodiacArr.length-1] + codeArr[codeArr.length-1] + "准";
    }else{
        return "？00准";
    }
    
    
}

function getResultNoTxt(codeStr,zodiacStr){
    
    
    if(null != codeStr && null != zodiacStr && codeStr.length > 0 && zodiacStr.length >0){
        let resStr = "";
        let codeArr = codeStr.split(",");
        let zodiacArr = zodiacStr.split(",");
        
        
        return zodiacArr[zodiacArr.length-1] + codeArr[codeArr.length-1];
    }else{
        return "？00";
    }
    
    
}

function getResultNoTxt0000(codeStr,zodiacStr){
    
    
    if(null != codeStr && null != zodiacStr && codeStr.length > 0 && zodiacStr.length >0){
        let resStr = "";
        let codeArr = codeStr.split(",");
        let zodiacArr = zodiacStr.split(",");
        
        
        return zodiacArr[zodiacArr.length-1] + codeArr[codeArr.length-1];
    }else{
        return "0000";
    }
    
    
}

//获取波
function getBo(str){
	
	let bo = "";
	
	switch(str){
		case "red":
			bo = "红";
		break;
		case "green":
			bo = "绿";
		break;
		case "blue":
			bo = "蓝";
		break;
	}
	
	return bo;
}


function getBoSel(str,spStr){
	
	if (null == spStr || spStr.length <= 0){
	    str += "波";
	    return str;
	}else{
		let resStr = "";
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		
		for(let i = 0 ; i < str.length ; i++){
			
		    if(str[i] == getBo(sp)){
		        resStr += `<span style="background-color: #FFFF00">${str[i]}</span>`;
				if(i == str.length-1){
					resStr += `<span style="background-color: #FFFF00">波</span>`;
				}
		    }else{
		        resStr += str[i];
				if(i == str.length-1){
					resStr += "波";
				}
		    }
		}
		
		return resStr;
	}
	
}



function getBoSelSbzt(str,spStr){
	
	let resStr = "";
	let strArr = str.split(",");
	
	if (null == spStr || spStr.length <= 0){
		strArr.forEach(el=>{
			resStr += el;
		})
	    return resStr;
	}else{
		
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		
		for(let i = 0 ; i < strArr.length ; i++){
		    if(strArr[i][0] == getBo(sp)){
		        resStr += `<span style="background-color: #FFFF00">${strArr[i]}</span>`;
		    }else{
				resStr += strArr[i];
		    }
		}
		
		return resStr;
	}
	
}

function getBoSelSbztMa22(str,spStr){
	
	let resStr = "";
	let strArr = str.split(",");
	
	if (null == spStr || spStr.length <= 0){
		strArr.forEach((el,index)=>{
			resStr += el[0];
			if(index != strArr.length -1){
				resStr += "+"
			}
		})
	    return resStr;
	}else{
		
		let spArr = spStr.split(",");
		let sp = spArr[spArr.length-1];
		
		for(let i = 0 ; i < strArr.length ; i++){
		    if(strArr[i][0] == getBo(sp)){
		        resStr += `<span style="background-color: #FFFF00">${strArr[i][0]}</span>`;
		    }else{
				resStr += strArr[i][0];
		    }
			if(i != strArr.length -1){
				resStr += "+"
			}
		}
		
		return resStr;
	}
	
}





function getIsSingle(num){
	
	let str = "";
	
	if(num - 0){
		if((num - 0)%2 == 0){
			str = "双"
		}else{
			str = "单"
		}
		return str;
		
	}else{
		return num;
	}
}

function getSingleSel(str,spStr){
	
	if (null == spStr || spStr.length <= 0){
	    str += "数";
	    return str;
	}else{
		let resStr = "";
		let spArr = spStr.split(",");
		let sp = getIsSingle(spArr[spArr.length-1]);
		
		if(str == sp){
			
			resStr += `<span style="background-color: #FFFF00">${str}数</span>`;
		}else{
			resStr = str + "数";
		}
		return resStr;
	}
}


function getBigOrSmall(arr,code,str){
	
	let res = "";
	let resStr = "";
	
	if(null != arr && null != code && arr.length > 0 && code.length > 0){
		let codeArr = code.split(",");
		
		arr.forEach(el=>{
			let elArr = el.code.split(",");
			elArr.forEach(item=>{
				if(item == codeArr[codeArr.length-1]){
					res = el.name
				}
			})
		})
		
		if(str == res){
			resStr = `<span style="background-color: #FFFF00">${str}</span>`;
		}else{
			resStr = str
		}
		return resStr;
	}else{
		return str;
	}
	
}

//yx
function getTxtBcAndNum(str,spStr){
	let resObj = {
		num: "？",
		resStr: ""
	}
	let strArr = str.split(",");
	if(null == spStr || spStr.length < 0){
		strArr.forEach(el=>{
			resObj.resStr += el
		})
		return resObj;
	}else{
		let spArr = spStr.split(",");
		let flag = false;
		resObj.num = 0;
		
		strArr.forEach(el=>{
			flag = false;
			spArr.forEach(item=>{
				if(el == zhuanzi(item)){
					flag = true;
				}
			})
			if(flag){
				resObj.resStr += `<span style="background-color: #FFFF00">${el}</span>`;
				resObj.num++;
			}else{
				resObj.resStr += el
			}
		})
		return resObj;
	}
}


//wuxing 
function getFiveSel(arr,code,str){
	
	let res = "";
	let resStr = "";
	let strArr = str.split(",");
	
	if(null != arr && null != code && arr.length > 0 && code.length > 0){
		let codeArr = code.split(",");
		
		arr.forEach(el=>{
			let elArr = el.code.split(",");
			elArr.forEach(item=>{
				if(item == zhuanzi(codeArr[codeArr.length-1])){
					res = el.name
				}
			})
		})
		strArr.forEach(el=>{
			
			if(el == res){
				resStr += `<span style="background-color: #FFFF00">${el}</span>`;
			}else{
				resStr += el
			}
		})
		
		return resStr;
	}else{
		
		strArr.forEach(el=>{
			resStr += el;
		})
		
		return resStr;
	}
}

function getBxelRes(code){
	
	let resStr = "";
	if(null == code || code.length <= 0){
		resStr = "00-00-00-00-00-00特00"
	}else{
		let codeArr = code.split(",");
		codeArr.forEach((el,index)=>{
			
			resStr += el;
			if(index < codeArr.length - 2){
				resStr += "-"
			}else if(index == codeArr.length - 2){
				resStr += "特"
			}
		})
	}
	return resStr;
}


function getBcDpez(code,str,bool){
	
	let resStr = "";
	let strArr = str.split(",");
	
	if(null == code || code.length <= 0){
		strArr.forEach((el,index)=>{
			resStr += el;
			if(bool && index < strArr.length-1){
				resStr += ".";
			}
		})
	}else{
		let step = 0;
		let codeArr = code.split(",");
		strArr.forEach(el=>{
			codeArr.forEach(item=>{
				if(el == item){
					step++
				}
			})
		})
		
		strArr.forEach((el,index)=>{
			if(step == strArr.length){
				resStr += `<span style="background-color: #FFFF00">${el}</span>`;
			}else{
				resStr += el;
			}
			if(bool && index < strArr.length-1){
				resStr += ".";
			}
		})
	}
	return resStr;
}


function getBcSqbz(spStr,str,bool){
	let resStr = ""
	let strArr = str.split(",");
	if(null == spStr || spStr.length < 0){
		strArr.forEach((el,index)=>{
			resStr += el
			if(bool && index < strArr.length-1){
				resStr += ".";
			}
		})
		return resStr;
	}else{
		let spArr = spStr.split(",");
		let flag = false;
		strArr.forEach((el,index)=>{
			flag = false;
			spArr.forEach(item=>{
				if(el == zhuanzi(item)){
					flag = true;
				}
			})
			if(flag){
				resStr += `<span style="background-color: #FFFF00">${el}</span>`;
			}else{
				resStr += el
			}
			if(bool && index < strArr.length-1){
				resStr += ".";
			}
		})
		return resStr;
	}
}
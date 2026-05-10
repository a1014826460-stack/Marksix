$.ajax({
    url: httpApi + `/api/kaijiang/qxbm?web=${API_WEB}&type=${type}`,
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            // data = data.slice(0, 1);
            for(let i in data){
                
                let result = '00'
                
                let content = data[i].xiao.split(',')
                let code = data[i].code.split(',')
                let s7 = selNumBcMa22(data[i].xiao,data[i].res_sx)
                let s5 = selNumBcMa22(data[i].xiao.substr(0,9),data[i].res_sx)
                let s3 = selNumBcMa22(data[i].xiao.substr(0,5),data[i].res_sx)
                let s1 = selNumBcMa22(data[i].xiao.substr(0,1),data[i].res_sx)
				
				let c7 = selNumBc(data[i].code,data[i].res_code)
				let c5 = selNumBc(data[i].code.substr(0,14),data[i].res_code)
				let p =  selNumBcMa22(data[i].ping,data[i].res_sx)
				let y = selNumBcMa22(content[0],data[i].res_sx)+selNumBc(code[0],data[i].res_code)
				
				let all_str = s7+c7+p+y
				if(null == data[i].res_code || data[i].res_code.length == 0 || all_str.indexOf('span') !=-1){
                htmlBoxList = htmlBoxList + ` 
<table width='100%' border='1' style='box-sizing: border-box; font-family: PingFangSC-Regular, &quot;Microsoft YaHei&quot;, Helvetica; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-style: initial; text-decoration-color: initial; font-size: 18px; border-collapse: collapse; border-spacing: 0px; font-weight: bold; color: rgb(0, 0, 0); border: 0px none; margin: 0px; padding: 0px;'>
	<thead style='box-sizing: border-box; margin: 0px; padding: 0px;'>
		<tr style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			<th style='box-sizing: border-box; font-size: 24px; color: rgb(255, 255, 255); margin: 0px; padding: 5px; background: rgb(255, 102, 102) center top'>
			<span style='box-sizing: border-box; font-weight: 400;'>浅月流歌</span>★一肖一码
			独家火爆</th>
		</tr>
	</thead>
</table>
<table width='100%' border='1' style='box-sizing: border-box; font-family: PingFangSC-Regular, &quot;Microsoft YaHei&quot;, Helvetica; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-style: initial; text-decoration-color: initial; font-size: 18px; border-collapse: collapse; border-spacing: 0px; font-weight: bold; color: rgb(0, 0, 0); border: 0px none; margin: 0px; padding: 0px;'>
	<tbody style='box-sizing: border-box;'>`
				}

	if(null == data[i].res_code || data[i].res_code.length == 0 || s7.indexOf('span') != -1){
		htmlBoxList +=`
		<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px'>
			<font color='#0000FF' face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			${data[i].term}期七肖：</font><font face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>${s7}</font></td>
		</tr>`
	}
	if(null == data[i].res_code || data[i].res_code.length == 0 ||  s5.indexOf('span') != -1){
		htmlBoxList +=`
	
		<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px' height='38'>
			<font color='#0000FF' face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			${data[i].term}期五肖：</font><font face='微软雅黑' style='box-sizing: border-box; '>${s5}</font></td>
		</tr>`
	}
	if(null == data[i].res_code || data[i].res_code.length == 0 || s3.indexOf('span') != -1){
		htmlBoxList +=
		`<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px'>
			<font color='#0000FF' face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			${data[i].term}期三肖：</font><font face='微软雅黑'>${s3}</font></td>
		</tr>`
	}
	if(null == data[i].res_code || data[i].res_code.length == 0 ||  s1.indexOf('span') != -1){
		htmlBoxList +=
		`
		<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px'>
			<font color='#0000FF' face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			${data[i].term}期一肖：</font><font face='微软雅黑' style='box-sizing: border-box; '>${s1}</font><font face='微软雅黑'>√</font></td>
		</tr>`
	}
	if(null == data[i].res_code || data[i].res_code.length == 0 || c7.indexOf('span') != -1){
		htmlBoxList +=`<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px'>
			<font color='#0000FF' style='box-sizing: border-box; margin: 0px; padding: 0px;' face='微软雅黑'>
			${data[i].term}期八码：</font><font face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>${c7}</font></td>
		</tr>`
	}
	if(null == data[i].res_code || data[i].res_code.length == 0 || c5.indexOf('span') != -1){
		htmlBoxList +=`<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px'>
			<font color='#0000FF' face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			${data[i].term}期五码：</font><font face='微软雅黑' style='box-sizing: border-box; margin: 0px; padding: 0px;'>${c5}</font></td>
		</tr>`
	}
	if(null == data[i].res_code || data[i].res_code.length == 0 || p.indexOf('span') != -1){
		htmlBoxList +=`<tr style='box-sizing: border-box;'>
			<td style='border:1px solid #cccccc; box-sizing: border-box; margin: 0px; padding: 5px'>
			<font face='微软雅黑' style='box-sizing: border-box;'>
			<font color='#0000FF' style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			${data[i].term}期</font><font color='#0000FF' style='box-sizing: border-box;'>平特</font><font color='#0000FF' style='box-sizing: border-box; margin: 0px; padding: 0px;'>：</font></font><font face='微软雅黑' style='box-sizing: border-box; '>${p}${p}${p}</font></td>
		</tr>`
	}
	htmlBoxList += `</table>`
	if(null == data[i].res_code || data[i].res_code.length == 0 || y.indexOf('span') != -1){
		htmlBoxList +=`<table width='100%' border='1' style='box-sizing: border-box; font-family: PingFangSC-Regular, &quot;Microsoft YaHei&quot;, Helvetica; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-style: initial; text-decoration-color: initial; font-size: 18px; border-collapse: collapse; border-spacing: 0px; font-weight: bold; color: rgb(0, 0, 0); border: 0px none; margin: 0px; padding: 0px;'>
			<thead style='box-sizing: border-box; margin: 0px; padding: 0px;'>
			</thead>
			<tbody style='box-sizing: border-box;'>
				<tr style='box-sizing: border-box;'>
					<th style='box-sizing: border-box; margin: 0px; padding: 5px;'>
					${data[i].term}期一肖一码：<font color='#FF0000' style='box-sizing: border-box; margin: 0px; padding: 0px;'>（ 
					${y}）</font>跟者发财</th>
				</tr>
		</table>
  
         `}
        }
	}
        
        htmlBox = `

        
        `+htmlBoxList+` 
`
        
        
        $(".wxbmBox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});   


 



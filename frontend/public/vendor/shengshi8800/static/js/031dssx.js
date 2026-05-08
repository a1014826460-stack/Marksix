var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/dssx?web=${web}&type=${type}`, 
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            
            for(let i in data){
                let d = data[i]
                let result = '00'
                let resCode = (data[i].res_code || '').split(",");
                let codeSplit = (d.res_code || '').split(',');
                let sxSplit = (d.res_sx || '').split(',');
                let resSx = (data[i].res_sx||'').split(",");
                let code = codeSplit[codeSplit.length - 1] || '';
                let sx = sxSplit[sxSplit.length - 1] || '';
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let x1 = d.xiao_1.split(',');
                let x2 = d.xiao_2.split(',');

                let b = false;
                let c1 = [];
                for (let i = 0; i < x1.length; i++) {
                    if (sx && x1[i].indexOf(sx) !== -1) {
                        b = true;
                        c1.push(`<span style="background-color: #FFFF00">${x1[i]}</span>`);
                    }else {
                        c1.push(`${x1[i]}`)
                    }
                }
                let c2 = [];
                for (let i = 0; i < x2.length; i++) {
                    if (sx && x2[i].indexOf(sx) !== -1) {
                        b = true;
                        c2.push(`<span style="background-color: #FFFF00">${x2[i]}</span>`);
                    }else {
                        c2.push(`${x2[i]}`)
                    }
                }

                
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
        <tr>
			<td>
				<font color='#000000'>${data[i].term}期:</font>
				<font color='3f7ee8'><span class='zl'>[单：${c1.join('')}][双：${c2.join('')}]</span> </font>
				开:${resSx[resSx.length-1]||'？'}${code||'00'}准
			</td>
		</tr>

    
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
	<div class='list-title'>台湾六合彩→<font color='#FF0000'>【</font>单双四肖<font color='#FF0000'>】</font>→ </div>
	<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF'
		bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        
        
        $(".dssxBox").html(replaceLegacySiteText(htmlBox))
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 






// 		<tr>
// 			<td>
// 				<font color='#000000'>269期:</font>
// 				<font color='3f7ee8'><span class='zl'>[单：鼠龙虎马][双：羊兔蛇鸡]</span> </font>开:？00准
// 			</td>
// 		</tr>



// 		<tr>
// 			<td>
// 				<font color='#000000'>266期:</font>
// 				<font color='3f7ee8'><span class='zl'>[单：龙<span
// 							style='background-color: #FFFF00'>虎</span>马猴][双：蛇牛羊兔]</span> </font>开:虎27准
// 			</td>
// 		</tr>




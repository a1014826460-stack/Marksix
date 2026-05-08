var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/danshuang?web=${web}&type=${type}`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data

        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let resCode = data[i].res_code.split(",");
                let resSx = data[i].res_sx.split(",");
                let result = '00'
                let codeSplit = (d.res_code || '').split(',');
                let sxSplit = (d.res_sx || '').split(',');
                let code = codeSplit[codeSplit.length - 1] || '';
                let sx = sxSplit[sxSplit.length - 1] || '';
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = JSON.parse(d.content);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }
                let c1 = [];
                let b = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        b = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}数</span>`);
                    }else {
                        c1.push(`${xiao[i]}数`)
                    }
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td width='28%'><font color='#000000'>第${data[i].term}期:</font></td>
	    <td><span class='zl'><font color='#0000FF'>${c1[0]}${c1[0]}${c1[0]}</font></span></td>
	    <td width='24%'><font color='#000000'>开${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}</font></td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' >台湾六合彩论坛『买啥开啥』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $("#msks").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});









/*


document.writeln("	 <div class='box pad' id='yxym'>");
document.writeln("		<div class='list-title' >台湾六合彩论坛『买啥开啥』 </div>");
document.writeln("		<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>");


document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第269期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>双数双数双数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开？00</font></td>");
document.writeln("			</tr>");

 
 

document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第268期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>双数双数双数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开羊22</font></td>");
document.writeln("			</tr>");

 
 

document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第267期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>双数双数双数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开蛇12</font></td>");
document.writeln("			</tr>");

 

document.writeln("			<tr>");
document.writeln("				<td width='28%'><font color='#000000'>第266期:</font></td>");
document.writeln("				<td><span class='zl'><font color='#0000FF'>单数单数单数</font></span></td>");
document.writeln("				<td width='24%'><font color='#000000'>开虎27</font></td>");
document.writeln("			</tr>");






document.writeln("		</table></div>");*/


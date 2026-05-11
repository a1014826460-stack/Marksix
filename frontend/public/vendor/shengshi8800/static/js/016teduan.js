var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getCodeDuan?web=${web}&type=${type}&num=12`,
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
                let code = resCode[resCode.length-1];
                let result = '00'
                let content = d.content.split(',');

                var hit = code && content.indexOf(code) !== -1;

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td><font color='#000000'>${data[i].term}期:开特码段</font><span class='zl'>【${content[0]}-${content[content.length-1]}】</span><font color='#000000'>开:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}${hit ? '准' : ''}</td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' >台湾六合彩论坛『特码段数』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".tmds").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});




/*



document.writeln("	");
document.writeln("		<div class='box pad\' id=\'yxym\'>");
document.writeln("		<div class=\'list-title\' >台湾六合彩论坛『特码段数』 </div>");
document.writeln("		<table border=\'1\' width=\'100%\' class=\'duilianpt1\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:开特码段</font><span class=\'zl\'>【23-32】</span><font color=\'#000000\'>开:？00准</td>");
document.writeln("			</tr>");




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>266期:开特码段</font><span class=\'zl\'>【21-32】</span><font color=\'#000000\'>开:虎27准</td>");
document.writeln("			</tr>");




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>265期:开特码段</font><span class=\'zl\'>【16-35】</span><font color=\'#000000\'>开:牛16准</td>");
document.writeln("			</tr>");




document.writeln("			<tr>");
document.writeln("				<td><font color=\'#000000\'>263期:开特码段</font><span class=\'zl\'>【06-17】</span><font color=\'#000000\'>开:龙13准</td>");
document.writeln("			</tr>");










 



document.writeln("		</table></div>");
document.writeln("		");*/


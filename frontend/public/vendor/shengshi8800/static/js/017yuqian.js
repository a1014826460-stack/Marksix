var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };

$.ajax({
    url: httpApi + `/api/kaijiang/getJuzi?web=${web}&type=${type}&num=juzi1`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = '',htmlBoxList = '',term=''

        let data = response.data.slice(0,10)

        if(data.length>0){
            for(let i in data){
                let d = data[i];
                let resCode = data[i].res_code.split(",");
                let resSx = data[i].res_sx.split(",");
                let result = '00'
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td>
        <span class='zl'><font color='#000000'>${d.term}期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</font><font color='#000099'><br>
        </font><font color='#0000FF'>${d.title}</font></span>
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title' >台湾六合彩论坛『欲钱解特』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".yqjt").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});



/*

document.writeln("	<div class='box pad' id='yxym'>");
document.writeln("	<div class='box pad' id='yxym'>");
document.writeln("		<div class='list-title' >台湾六合彩论坛『欲钱解特』 </div>");
document.writeln("		<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2'>");


document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>269期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开？00准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>穷秀才不名一文,雨脚如麻未断绝</font></span></td>");
document.writeln("			</tr>");
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>268期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开羊22准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>着意寻春懒便回,钿合儿我留一扇</font></span></td>");
document.writeln("			</tr>");
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>267期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开蛇12准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>草原一片绿无济,全凭牛羊进财源</font></span></td>");
document.writeln("			</tr>");
 
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>266期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开虎27准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>漠漠水田飞白鹭,清蒸藜炊黍饷东</font></span></td>");
document.writeln("			</tr>");
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>265期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开牛16准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>四夜静寂会情人,一来鲜花表真诚</font></span></td>");
document.writeln("			</tr>");
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>264期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开猪30准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>闰溪三日逃花雨,半夜二八来上滩</font></span></td>");
document.writeln("			</tr>");
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>263期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开龙13准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>着意寻春懒便回,钿合儿我留一扇</font></span></td>");
document.writeln("			</tr>");
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>262期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开鸡44准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>一生争你死我活,相斗至死方罢休</font></span></td>");
document.writeln("			</tr>");
 
 

document.writeln("			<tr>");
document.writeln("				<td><span class='zl'><font color='#000000'>261期:</font><font color='#FF00FF'>欲钱解特诗</font><font color='#000000'>&nbsp; 开龙01准</font><font color='#000099'><br>");
document.writeln("				</font><font color='#0000FF'>有理反成无理亏,嗟叹好事反成非</font></span></td>");
document.writeln("			</tr>");
 
 


document.writeln("		</table></div>");
document.writeln("		");*/


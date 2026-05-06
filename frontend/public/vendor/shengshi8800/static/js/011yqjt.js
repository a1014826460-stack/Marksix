$.ajax({
    url: httpApi + `/api/kaijiang/getJuzi?web=${web}&type=${type}&num=yqmtm`,
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
                let title = d.title.split(',');
                let result = '00'
                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
	    <td><font color='#0000FF'>${d.term}期：欲钱买特码【</font><font color='#FF00FF'>开${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}</font><font color='#0000FF'>】</font><br>
	    <font color="#000000">【欲钱买</font></font>${title[0]}<font color='#000000'>的生肖】<br>
	    【欲钱买</font>${title[1]}<font color='#000000'>的生肖】<br>
	    【欲钱买</font>${title[2]}<font color='#000000'>的生肖】<br>
	    【欲钱买</font>${title[3]}<font color='#000000'>的生肖】
	    </font></span></td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title'>台湾六合彩论坛『欲钱解特』</div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1799'>
    `+htmlBoxList+`
 </table>
</div>

`
        $(".yqjt2").html(htmlBox)

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});
/*

document.writeln("	<div class='box pad' id='yxym'>");
document.writeln("		<div class='list-title'>台湾六合彩论坛『欲钱解特』</div>");
document.writeln("		<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1799'>");




 
 
 
 
document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>269期：欲钱买特码【</font><font color='#FF00FF'>开？00</font><font color='#0000FF'>】</font><br>");
document.writeln("<span class='zl'><font color='#000000'>");
document.writeln("【欲钱买</font>马不停蹄<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>飞龙在天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>牛气冲天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>引蛇出洞<font color='#000000'>的生肖】");
document.writeln("</font></span></td>");
document.writeln("</tr>");


 


document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>266期：欲钱买特码【</font><font color='#FF00FF'>开虎27</font><font color='#0000FF'>】</font><br>");
document.writeln("<span class='zl'><font color='#000000'>");
document.writeln("【欲钱买</font>虎虎生威<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>飞龙在天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>牛气冲天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>打狗看主<font color='#000000'>的生肖】");
document.writeln("</font></span></td>");
document.writeln("</tr>");


 
document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>264期：欲钱买特码【</font><font color='#FF00FF'>开猪30</font><font color='#0000FF'>】</font><br>");
document.writeln("<span class='zl'><font color='#000000'>");
document.writeln("【欲钱买</font>守株待兔<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>飞龙在天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>金鸡独立<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>猪头猪脑<font color='#000000'>的生肖】");
document.writeln("</font></span></td>");
document.writeln("</tr>");


document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>261期：欲钱买特码【</font><font color='#FF00FF'>开龙01</font><font color='#0000FF'>】</font><br>");
document.writeln("<span class='zl'><font color='#000000'>");
document.writeln("【欲钱买</font>虎虎生威<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>飞龙在天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>守株待兔<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>猪头猪脑<font color='#000000'>的生肖】");
document.writeln("</font></span></td>");
document.writeln("</tr>");

 
 
 
document.writeln("<tr>");
document.writeln("<td><font color='#0000FF'>260期：欲钱买特码【</font><font color='#FF00FF'>开牛40</font><font color='#0000FF'>】</font><br>");
document.writeln("<span class='zl'><font color='#000000'>");
document.writeln("【欲钱买</font>得意洋洋<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>打狗看主<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>牛气冲天<font color='#000000'>的生肖】<br>");
document.writeln("【欲钱买</font>猪头猪脑<font color='#000000'>的生肖】");
document.writeln("</font></span></td>");
document.writeln("</tr>");





document.writeln("");
document.writeln("		</table>");
document.writeln("		</div>");

*/

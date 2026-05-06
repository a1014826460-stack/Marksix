$.ajax({
    url: httpApi + `/api/kaijiang/getDjym?web=${web}&type=${type}`,
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
                let content = JSON.parse(d.code);
                for (let i in content) {
                    let c = content[i].split('|');
                    xiao.push(c[0].split('')[0])
                    xiaoV[i] = c[1];
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let b = false;
                for (let i = 0; i < xiao.length; i++) {
                    if (code && xiaoV[i].indexOf(code) !== -1) {
                        b = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr style='background: #FFFF00;'>
	    <td style='background-color: #CCFFCC; text-align: left'>
	        <span class='zl'><font color='#000000'>${data[i].term}期独家幽默：開:${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}准</font></span>
	    </td>
    </tr>
    <tr>
        <td style='text-align: left'><font color='#008000'>${d.content}</font><br>
        <span class='zl'><font color='#000000'>推荐特尾：：</font>${c1.join('')}</span></td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class='list-title'>台湾六合彩论坛『独家幽默<span class='zl'>』 </div>
    <table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1810'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".djym").html(htmlBox)

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});


/*

document.writeln("<div class='box pad' id='yxym'>");
document.writeln("<div class='list-title'>台湾六合彩论坛『独家幽默<span class='zl'>』 </div>");
document.writeln("<table border='1' width='100%' class='duilianpt1' bgcolor='#ffffff' cellspacing='0' bordercolor='#FFFFFF' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' cellpadding='2' id='table1810'>");

document.writeln("					<tr style='background: #FFFF00;'>");
document.writeln("");
document.writeln("				<td style='background-color: #CCFFCC; text-align: left'>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>269期独家幽默：開:？00准</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style='text-align: left'><font color='#008000'>独家幽默：小龙的父亲警告他说：“千万不能到表演脱衣舞的戏院去看表演！”小龙不解的问道：“为什么？”父亲严厉的说：“因为那里是败坏风俗的地方，你会看不到应该看的东西！”第二天晚上，小龙还是偷偷的去看了一场脱衣舞秀！果然，他真的在戏院里看到了他不应该看到的东西??他的父亲！</font><br>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>推荐特尾：：</font>023578</span></td>");
document.writeln("");
document.writeln("			</tr>");





document.writeln("					<tr style='background: #FFFF00;'>");
document.writeln("");
document.writeln("				<td style='background-color: #CCFFCC; text-align: left'>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>268期独家幽默：開:羊22准</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style='text-align: left'><font color='#008000'>独家幽默：搜索关注天天一笑笑网看更多冷笑话，有个腼腆的男孩终于鼓足勇气问心爱的女孩:你喜欢什么样的男孩子?女孩说:投缘的X男孩再问还是一样,他只好伤心的说:头扁一点的不行吗?</font><br>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>推荐特尾：：</font>1<span style='background-color: #FFFF00'>2</span>4567</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("					<tr style='background: #FFFF00;'>");
document.writeln("");
document.writeln("				<td style='background-color: #CCFFCC; text-align: left'>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>267期独家幽默：開:蛇12准</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style='text-align: left'><font color='#008000'>独家幽默：刚上微信和附近一女的聊天。问我在干嘛呢，我说在做红烧肉。她问就我一个人在家吗，我说是的。她说那我去你家吃红烧肉吧，我一听二话没说直接拉黑了、三十多块钱一斤的猪肉你想吃，门都没有！</font><br>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>推荐特尾：：</font>0<span style='background-color: #FFFF00'>2</span>3479</span></td>");
document.writeln("");
document.writeln("			</tr>");



document.writeln("					<tr style='background: #FFFF00;'>");
document.writeln("");
document.writeln("				<td style='background-color: #CCFFCC; text-align: left'>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>265期独家幽默：開:牛16准</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style='text-align: left'><font color='#008000'>独家幽默：在网吧上网中，旁边坐了个三四十岁的男人。我正玩呢眼光瞟了他屏幕一眼，貌似在QQ聊天，对方女的要他开视频， 这货竟然把摄像头调整对着我，然后他尿急去厕所。出于人道主义，我对着摄像头挖了一分钟鼻孔，然后那女的默默把视频关了。</font><br>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>推荐特尾：：</font>134<span style='background-color: #FFFF00'>6</span>78</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("					<tr style='background: #FFFF00;'>");
document.writeln("");
document.writeln("				<td style='background-color: #CCFFCC; text-align: left'>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>264期独家幽默：開:猪30准</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style='text-align: left'><font color='#008000'>独家幽默：男朋友最近做了一个小手术，躺在病床上一周之内不能下床。 我去医院照顾她，实在闲的无聊，就买了两根棒棒糖吃。 躺在床上的男友：“别吃了，我看着难受。” 我：“你怎么什么都管，你看着难受，我还难受呢，反正现在闲着也是闲着。”</font><br>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>推荐特尾：：</font><span style='background-color: #FFFF00'>0</span>13579</span></td>");
document.writeln("");
document.writeln("			</tr>");





document.writeln("					<tr style='background: #FFFF00;'>");
document.writeln("");
document.writeln("				<td style='background-color: #CCFFCC; text-align: left'>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>263期独家幽默：開:龙13准</font></span></td>");
document.writeln("");
document.writeln("			</tr>");
document.writeln("");
document.writeln("			<tr>");
document.writeln("");
document.writeln("				<td style='text-align: left'><font color='#008000'>独家幽默：在经历了漫长的十几小时飞机后，我终于如愿以偿的到达了，美国洛杉矶，啊！美国，他们说的空气，我一闻，果然是极其香甜的，完全没有雾霾，于是我摘下了在中国所戴的厚厚的口罩，换上了厚厚的防弹衣！</font><br>");
document.writeln("");
document.writeln("				<span class='zl'><font color='#000000'>推荐特尾：：</font>0<span style='background-color: #FFFF00'>3</span>5689</span></td>");
document.writeln("");
document.writeln("			</tr>");




document.writeln("");
document.writeln("</table></div>");

document.writeln("");*/

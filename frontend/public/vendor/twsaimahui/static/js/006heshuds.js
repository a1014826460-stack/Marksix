$.ajax({
    url: httpApi + `/api/kaijiang/getHeds?web=${web}&type=${type}&num=2`,
    type: 'GET',
    dataType: 'json',
    success: function (response) {
        let htmlBox = '', htmlBoxList = '', term = ''

        let data = response.data
        let yinx = '';
        let yangx = '';
        if (data.length > 0) {
            for (let i in data) {
                let d = data[i]
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao = [];
                let xiaoV = [];
                let ma = [];
                let content = safeParseJSON(d.content, String(d.content || '').trim() ? [String(d.content)] : []);
                for (let i in content) {
                    let c = content[i].split('|');
                    if (c.length < 2 || !c[1]) {
                        // 供给数据可能是 `合双` 这种纯标签（没有 `标签|号码` 结构），
                        // 旧实现直接 JSON.parse 会抛错并让整个模块渲染不出来。
                        xiao.push(c[0]);
                        xiaoV[i] = '';
                        continue;
                    }
                    xiao.push(c[0])
                    xiaoV[i] = c[1];
                    if (c[0] === '阴肖') {
                        yinx = c[1].replaceAll(',','');
                    }else{
                        yangx = c[1].replaceAll(',','');
                    }
                    ma.push(...c[1].split(','));
                }

                let c1 = [];
                let zj = false;
                // 候选号码集合缺失时不能给出任何判定：既不能假命中，也不能假不中。
                // 供给数据只有 `合单` / `合双` 纯标签（没有 `标签|号码` 结构）时，
                // 旧实现把空串拿去 indexOf → 每期都显示「不中」。
                let hasCandidates = false;
                for (let i = 0; i < xiao.length; i++) {
                    // 合数单双的候选是一组号码（`合单|01,03,…`），必须做**集合精确匹配**：
                    // 用 indexOf 会让特码 `11` 命中候选串里的 `11`（属于合双）、或让 `3`
                    // 命中 `37`，把「不中」显示成「中」。
                    // 号码集合来自后端 `/api/kaijiang/getHeds`（读 public.fixed_data 的「合单双」）。
                    let candidates = String(xiaoV[i] || '').split(',').map(v => v.trim()).filter(v => v !== '');
                    if (candidates.length > 0) {
                        hasCandidates = true;
                    }
                    let hit = !!(code && candidates.length > 0 && candidates.indexOf(code) !== -1);
                    if (hit) {
                        zj = true;
                        c1.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c1.push(`${xiao[i]}`)
                    }
                }
                let verdict = '';
                if (sx && code) {
                    verdict = !hasCandidates ? '??' : (zj ? '中' : '不中');
                } else if (!sx) {
                    verdict = '??';
                }

                htmlBoxList += ` 
 
\t\t\t\t\t\t\t\t\t<tr>
\t\t\t<td align='center' height=40><b>
\t\t\t<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${d.term}期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${c1.join('')}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>${sx||'？'}${code||'00'}</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>${verdict}</font></b></td>
\t\t</tr>
            `
            }
        }
        htmlBoxList = `
<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 			


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>合数中特</font></font></font></b></td>

		</tr>	

            ${htmlBoxList}
            </table>
        `;
        $(".l9").html(htmlBoxList)
    },
    error: function (xhr, status, error) {
        console.error('Error:', error);
    }
});

/*



<table border='1' width='100%' cellpadding='0' cellspacing='0' bgcolor='#FFFFFF' bordercolor='#D4D4D4' style='border-collapse: collapse'>

 			


	<tr>

		<td class='center f13 black l150' height='29' align='center' bgcolor='#FF0000'>

				<b>
				<font size='4'><font color='#FFFF00' face='微软雅黑'>&nbsp;</font><font face='微软雅黑'><font color='#FFFF00'> </font><font color='#FFFFFF'>合数中特</font></font></font></b></td>

		</tr>

























									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>268期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>？00</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>







									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>267期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>蛇12</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>


 

									<tr>
			<td align='center' height=40><b>
			<font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>265期</font><font color='#339933' style='font-size: 14pt' face='方正粗黑宋简体'>澳合数</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>【</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>合单</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>】开</font><font color='#FF0000' style='font-size: 14pt' face='方正粗黑宋简体'>牛16</font><font color='#000000' style='font-size: 14pt' face='方正粗黑宋简体'>中</font></b></td>
		</tr>




 


 
 
 
 
 
 
 

						</table>
*/



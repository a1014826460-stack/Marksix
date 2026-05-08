
$.ajax({
    url: httpApi + `/api/kaijiang/getXmx1?web=${web}&type=${type}&num=9`,
    type: 'GET', 
    dataType: 'json', 
    success: function(response) {
        
        let htmlBox = '',htmlBoxList = '',term=''
        
        let data = response.data
        
        if(data.length>0){
            
            for(let i in data){
                let result = '00'
                let d = data[i];
                let resCode = d.res_code.split(',');
                let resSx = d.res_sx.split(',');
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

                let c = [];
                for (let i = 0; i < xiao.length; i++) {
                    if (sx && xiao[i].indexOf(sx) !== -1) {
                        c.push(`<span style="background-color: #FFFF00">${xiao[i]}</span>`);
                    }else {
                        c.push(`${xiao[i]}`)
                    }
                }
                let c1 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c1.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c1.push(`${ma[i]}`)
                    }
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：${c1.slice(0,10).join(',')}</span></td>
    </tr>
    <tr>
      <td>${d.term}期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>${c[0]}</span>
        <font color='#000000'>-统计</font></td>
      <td>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}中</td>
    </tr>
    <tr>
      <td>${d.term}期:②肖</td>
      <td style='color: #FF0000;'>${c.slice(0,2).join('')}</td>
      <td>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}中</td>
     </tr>
    <tr>
      <td>${d.term}期:③肖</td>
      <td style='color: #FF0000;'>${c.slice(0,3).join('')}</td>
      <td>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}中</td>
    </tr>
    <tr>
      <td>${d.term}期:⑤肖</td>
      <td style='color: #FF0000;'>${c.slice(0,5).join('')}</td>
      <td>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}中</td>
    </tr>
    <tr>
      <td>${d.term}期:⑦肖</td>
      <td style='color: #FF0000;'>${c.slice(0,7).join('')}</td>
      <td>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}中</td>
    </tr>
    <tr>
      <td>${d.term}期:⑨肖</td>
      <td style='color: #FF0000;'>${c.join('')}</td>
      <td>${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}中</td>
    </tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td>
    </tr>
            `}
        }
        
        htmlBox = `
<div class='box pad' id='yxym'>
  <div class='list-title'>名震全坛【台湾六合彩论坛 】等您来看</div>
  <table border='1' width='100%' cellpadding='0' cellspacing='0' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' bgcolor='#FFFFFF' class='qxtable yxym' id='table1793'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".jxztBox").html(htmlBox)
        
    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
}); 



/*

<div class='box pad' id='yxym'>
  <div class='list-title'>名震全坛【台湾六合彩论坛 】等您来看</div>
  <table border='1' width='100%' cellpadding='0' cellspacing='0' bordercolorlight='#FFFFFF' bordercolordark='#FFFFFF' bgcolor='#FFFFFF' class='qxtable yxym' id='table1793'>
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：44.20.05.29.10.34.49.25.39.15.07.31</span></td>
    </tr>
    <tr>
      <td>269期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>鸡44</span>
        <font color='#000000'>-统计</font></td>
      <td>？00中</td></tr>
    <tr>
      <td>269期:②肖</td>
      <td style='color: #FF0000;'>鸡鼠</td>
      <td>？00中</td></tr>
    <tr>
      <td>269期:③肖</td>
      <td style='color: #FF0000;'>鸡鼠羊</td>
      <td>？00中</td></tr>
    <tr>
      <td>269期:⑤肖</td>
      <td style='color: #FF0000;'>鸡鼠羊龙虎</td>
      <td>？00中</td></tr>
    <tr>
      <td>269期:⑦肖</td>
      <td style='color: #FF0000;'>鸡鼠羊龙虎狗牛</td>
      <td>？00中</td></tr>
    <tr>
      <td>269期:⑨肖</td>
      <td style='color: #FF0000;'>鸡鼠羊龙虎狗牛兔猴</td>
      <td>？00中</td></tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td></tr>
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：33.45.05.17.03.27.25.37.38.26.22.34</span></td>
    </tr>
    <tr>
      <td>268期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>猴33</span>
        <font color='#000000'>-统计</font></td>
      <td>羊22中</td></tr>
    <tr>
      <td>268期:②肖</td>
      <td style='color: #FF0000;'>猴鼠</td>
      <td>羊22中</td></tr>
    <tr>
      <td>268期:③肖</td>
      <td style='color: #FF0000;'>猴鼠虎龙</td>
      <td>羊22中</td></tr>
    <tr>
      <td>268期:⑤肖</td>
      <td style='color: #FF0000;'>猴鼠虎龙兔</td>
      <td>羊22中</td></tr>
    <tr>
      <td>268期:⑦肖</td>
      <td style='color: #FF0000;'>猴鼠虎龙兔
        <span style='background-color: #FFFF00'>羊</span>猪</td>
      <td>羊22中</td></tr>
    <tr>
      <td>268期:⑨肖</td>
      <td style='color: #FF0000;'>猴鼠虎龙兔
        <span style='background-color: #FFFF00'>羊</span>猪马狗</td>
      <td>羊22中</td></tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td></tr>
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：40.28.20.32.19.31.11.23.39.03.24.36</span></td>
    </tr>
    <tr>
      <td>267期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>牛40</span>
        <font color='#000000'>-统计</font></td>
      <td>蛇12中</td></tr>
    <tr>
      <td>267期:②肖</td>
      <td style='color: #FF0000;'>牛鸡</td>
      <td>蛇12中</td></tr>
    <tr>
      <td>267期:③肖</td>
      <td style='color: #FF0000;'>牛鸡狗</td>
      <td>蛇12中</td></tr>
    <tr>
      <td>267期:⑤肖</td>
      <td style='color: #FF0000;'>牛鸡狗马虎</td>
      <td>蛇12中</td></tr>
    <tr>
      <td>267期:⑦肖</td>
      <td style='color: #FF0000;'>牛鸡狗马虎
        <span style='background-color: #FFFF00'>蛇</span>猴</td>
      <td>蛇12中</td></tr>
    <tr>
      <td>267期:⑨肖</td>
      <td style='color: #FF0000;'>牛鸡狗马虎
        <span style='background-color: #FFFF00'>蛇</span>猴兔龙</td>
      <td>蛇12中</td></tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td></tr>
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：20.32.05.17.30.42.12.24.14.02.10.22</span></td>
    </tr>
    <tr>
      <td>264期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>鸡20</span>
        <font color='#000000'>-统计</font></td>
      <td>猪30中</td></tr>
    <tr>
      <td>264期:②肖</td>
      <td style='color: #FF0000;'>鸡鼠</td>
      <td>猪30中</td></tr>
    <tr>
      <td>264期:③肖</td>
      <td style='color: #FF0000;'>鸡鼠
        <span style='background-color: #FFFF00'>猪</span></td>
      <td>猪30中</td></tr>
    <tr>
      <td>264期:⑤肖</td>
      <td style='color: #FF0000;'>鸡鼠
        <span style='background-color: #FFFF00'>猪</span>蛇兔</td>
      <td>猪30中</td></tr>
    <tr>
      <td>264期:⑦肖</td>
      <td style='color: #FF0000;'>鸡鼠
        <span style='background-color: #FFFF00'>猪</span>蛇兔羊龙</td>
      <td>猪30中</td></tr>
    <tr>
      <td>264期:⑨肖</td>
      <td style='color: #FF0000;'>鸡鼠
        <span style='background-color: #FFFF00'>猪</span>蛇兔羊龙马虎</td>
      <td>猪30中</td></tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td></tr>
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：13.37.15.27.10.22.36.48.08.32.23.35</span></td>
    </tr>
    <tr>
      <td>263期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>
          <span style='background-color: #FFFF00'>龙13</span></span>
        <font color='#000000'>-统计</font></td>
      <td>龙13中</td></tr>
    <tr>
      <td>263期:②肖</td>
      <td style='color: #FF0000;'>
        <span style='background-color: #FFFF00'>龙</span>虎</td>
      <td>龙13中</td></tr>
    <tr>
      <td>263期:③肖</td>
      <td style='color: #FF0000;'>
        <span style='background-color: #FFFF00'>龙</span>虎羊</td>
      <td>龙13中</td></tr>
    <tr>
      <td>263期:⑤肖</td>
      <td style='color: #FF0000;'>
        <span style='background-color: #FFFF00'>龙</span>虎羊蛇鸡</td>
      <td>龙13中</td></tr>
    <tr>
      <td>263期:⑦肖</td>
      <td style='color: #FF0000;'>
        <span style='background-color: #FFFF00'>龙</span>虎羊蛇鸡马猴</td>
      <td>龙13中</td></tr>
    <tr>
      <td>263期:⑨肖</td>
      <td style='color: #FF0000;'>
        <span style='background-color: #FFFF00'>龙</span>虎羊蛇鸡马猴兔牛</td>
      <td>龙13中</td></tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td></tr>
    <tr>
      <td colspan='3' style='background: #f7f7f7; color: #FF0000;'>
        <span class='jx'>精选：18.30.07.19.21.33.46.34.05.17.39.03</span></td>
    </tr>
    <tr>
      <td>262期:①肖</td>
      <td style='color: #FF0000;'>
        <font color='#000000'>规律-</font>
        <span style='font-size: 22pt'>猪18</span>
        <font color='#000000'>-统计</font></td>
      <td>鸡44中</td></tr>
    <tr>
      <td>262期:②肖</td>
      <td style='color: #FF0000;'>猪狗</td>
      <td>鸡44中</td></tr>
    <tr>
      <td>262期:③肖</td>
      <td style='color: #FF0000;'>猪狗猴</td>
      <td>鸡44中</td></tr>
    <tr>
      <td>262期:⑤肖</td>
      <td style='color: #FF0000;'>猪狗猴羊鼠</td>
      <td>鸡44中</td></tr>
    <tr>
      <td>262期:⑦肖</td>
      <td style='color: #FF0000;'>猪狗猴羊鼠虎
        <span style='background-color: #FFFF00'>鸡</span></td>
      <td>鸡44中</td></tr>
    <tr>
      <td>262期:⑨肖</td>
      <td style='color: #FF0000;'>猪狗猴羊鼠虎
        <span style='background-color: #FFFF00'>鸡</span>马牛</td>
      <td>鸡44中</td></tr>
    <tr>
      <td colspan='3'>台湾六合彩论坛 ,让赚钱的节奏停不下来</td></tr>
  </table>
</div>*/

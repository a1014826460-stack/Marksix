var replaceLegacySiteText = window.__legacyReplaceSiteText || function(value) { return value; };


$.ajax({
    url: httpApi + `/api/kaijiang/getCode?web=${web}&type=${type}&num=24`,
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
                let codeSplit = d.res_code.split(',');
                let sxSplit = d.res_sx.split(',');
                let code = codeSplit[codeSplit.length-1]||'';
                let sx = sxSplit[sxSplit.length-1]||'';
                let xiao =  [];
                let xiaoV =  [];
                let ma = d.content.split(',');

                let c2 = [];
                for (let i = 0; i < ma.length; i++) {
                    if (code && ma[i].indexOf(code) !== -1) {
                        c2.push(`<span style="background-color: #FFFF00">${ma[i]}</span>`);
                    }else {
                        c2.push(`${ma[i]}`)
                    }
                }

                //console.log(ma)
                htmlBoxList = htmlBoxList + ` 
		
	<tr>
        <td>
            <font color='#000000'>${d.term}期:《经典24码》开【${resSx[resSx.length-1]||'？'}${resCode[resCode.length-1]||'00'}】</font> <br>
            <span class=\'zl\'>{${c2.slice(0,12).join('.')}}</span><br>
            <span class=\'zl\'>{${c2.slice(12).join('.')}}</span>
        </td>
    </tr>
            `}
        }

        htmlBox = `
<div class='box pad' id='yxym'>
    <div class=\'list-title\'>台湾六合彩论坛（经典24码） </div>
    <table border=\'1\' width=\'100%\' class=\'duilianpt\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>
        `+htmlBoxList+` 
 </table>
</div>

`
        $(".jd24").html(replaceLegacySiteText(htmlBox))

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});






/*


document.writeln("");
document.writeln("			 	<div class=\'box pad\' id=\'yxym\'>");
document.writeln("		<div class=\'list-title\'>台湾六合彩论坛（经典24码） </div>");
document.writeln("		<table border=\'1\' width=\'100%\' class=\'duilianpt\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\'>");
document.writeln("			<tr>");
document.writeln("				<td>");
document.writeln("		<table border=\'1\' width=\'100%\' class=\'duilianpt\' bgcolor=\'#ffffff\' cellspacing=\'0\' bordercolor=\'#FFFFFF\' bordercolorlight=\'#FFFFFF\' bordercolordark=\'#FFFFFF\' cellpadding=\'2\' id=\'table10\'>");
document.writeln("			");
document.writeln("			");









document.writeln("				<tr>");
document.writeln("				<td><font color=\'#000000\'>269期:《经典24码》开【？00】</font> <br>");
document.writeln("				<span class=\'zl\'>{07.08.09.16.17.18.19.20.24.25.26.27}</span><br><span class=\'zl\'>{28.34.35.36.37.39.42.43.44.45.46.49}</span></td>");
document.writeln("			</tr>");



  
document.writeln("			");
document.writeln("		</table></td>");
document.writeln("			</tr>");
document.writeln("		</table></div>");*/


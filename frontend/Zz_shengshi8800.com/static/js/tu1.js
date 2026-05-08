
$.ajax({
    url: httpApi + `/api/post/getList?type=${type}&web=${web}&pc=305`,
    type: 'GET',
    dataType: 'json',
    success: function(response) {

        let htmlBox = `
        `

        let data = response.data

        let li = [];
        let images = [];
        if(data.length>0){
            for(let i in data){
                let d = data[i]
                htmlBox+=`
<a href="${d.cover_image}" target="_blank" style="width:100%;    display: inline-block;">
<img src='${d.cover_image}' class='zoom'width="100%"/></a>
                `
            }
        }
        htmlBox=`
<div style="display: flex;justify-content: space-around;flex-flow: wrap;">    
${htmlBox}
            </div>       
        `

        $("#xlnxjImg").html(htmlBox)

    },
    error: function(xhr, status, error) {
        console.error('Error:', error);
    }
});

 sx = {
    "鼠": "05,17,29,41",
    "牛": "04,16,28,40",
    "虎": "03,15,27,39",
    "兔": "02,14,26,38",
    "龙": "01,13,25,37,49",
    "蛇": "12,24,36,48",
    "马": "11,23,35,47",
    "羊": "10,22,34,46",
    "猴": "09,21,33,45",
    "鸡": "08,20,32,44",
    "狗": "07,19,31,43",
    "猪": "06,18,30,42",
}
 function getNumBySx(sxName){
    for (let i in sx) {
        if (sx[i].indexOf(sxName) !== -1) {
            return i;
        }
    }
    return '';
}

 function getLocationSearch(){
    let search = window.location.search.replace('?','');
    let obj = {};
    search.split('&').forEach(item => {
        let split = item.split('=');
        obj[split[0]] = split[1];
    })
    return obj;
}

function getZjNum(str,array){
    for (let i = 0; i < array.length; i++) {
        let arr = array[i];
        if (str.indexOf(arr) !== -1) {
            return arr;
        }
    }
}
function getZjIndex(str,array){
    for (let i = 0; i < array.length; i++) {
        let arr = array[i];
        if (!arr) continue;
        if (str.indexOf(arr) !== -1) {
            return i;
        }
    }
}

 const colro = {
     "红": "01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46",
     "绿": "05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49",
     "蓝": "03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48",
 }
 function getNumsByColor(colorName) {
     return colro[colorName.trim()];
 }

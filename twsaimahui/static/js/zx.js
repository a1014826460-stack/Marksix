// 推 (Vue 组件 + apiClient)
{
    var scripts = document.getElementsByTagName('script');
    var id = scripts[scripts.length - 1].getAttribute('dId');
    if (!id) id = 'zx5';
    var template = '<link rel=\'stylesheet\' type=\'text/css\' href=\'/components/zx/zx.css\'/><table class=\'msmjksm\' width=\'100%\' border=\'0\'><tbody><tr v-for="(parent,index) in d1" :key="index"><td v-for="(item,index) in parent" :key="item.id"><a target=\'_blank\' :href=\'to+"?id="+item.id\' v-html="item.title"></a></td></tr></tbody></table>';
    Vue.createApp({
        data: function () {
            return {
                to: '/components/detail.html',
                d1: [],
                error: false
            };
        },
        created: function () {
            this.loadList();
        },
        template: template,
        methods: {
            loadList: function () {
                var self = this;
                window.apiClient.get('/api/post/getList', {
                    web: window.web,
                    type: window.type,
                    pc: 72
                }).then(function (res) {
                    var data = res.data && res.data.data ? res.data.data : [];
                    if (!data.length) {
                        self.error = true;
                        return;
                    }
                    var count = 0;
                    while (count < data.length) {
                        var beforeCount = count;
                        count += 2;
                        self.d1[count / 2 - 1] = data.slice(beforeCount, count);
                    }
                }).catch(function () {
                    self.error = true;
                });
            }
        }
    }).mount('#' + id);
}

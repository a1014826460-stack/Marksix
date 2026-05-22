# twcaibawang 新开发接口 API 文档

本文件定义 `twcaibawang(web_id=5)` 第二阶段接入时建议新增的接口。

目标：

1. 支持首页榜单/详情页的数据化
2. 支持首页“组合型资料块”的动态化
3. 保持与现有项目接口风格一致，不影响现有 `/api/public/*`、`/api/legacy/*`

## 1. 设计原则

### 1.1 路由风格

建议统一新增到 Python 后端：

- `/api/vendor/articles`
- `/api/vendor/articles/{slug}`
- `/api/vendor/homepage-modules`

原因：

- 这批接口是站点内容层，不属于通用开奖接口
- 不应污染现有 `/api/public/site-page` 的标准预测模块结构
- 后续如果别的 vendor 站点也需要类似文章/组合块能力，可以继续复用这个命名空间

### 1.2 成功返回格式

建议统一为：

```json
{
  "ok": true,
  "data": {}
}
```

列表接口可额外返回分页字段：

```json
{
  "ok": true,
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 16
  }
}
```

### 1.3 失败返回格式

建议统一为：

```json
{
  "ok": false,
  "error": "错误说明"
}
```

参数错误示例：

```json
{
  "ok": false,
  "error": "site_id 必须为正整数"
}
```

## 2. 文章列表接口

用于支撑：

- 首页 `高手榜单`
- 首页 `绝杀榜`
- 后续其他榜单/栏目跳转页

---

### `GET /api/vendor/articles`

### 用途

按站点、栏目、期号查询文章列表。

### Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `site_id` | integer | 是 | 站点 ID，`twcaibawang` 建议传 `5` |
| `category` | string | 否 | 栏目分类，如 `expert-list`、`kill-rank` |
| `term` | string | 否 | 期号筛选，如 `125` |
| `page` | integer | 否 | 页码，默认 `1` |
| `page_size` | integer | 否 | 每页条数，默认 `20`，建议最大 `100` |
| `status` | string | 否 | `published` / `draft`，公开前端默认只传 `published` |

### 建议分类值

| category | 对应前端区域 |
| --- | --- |
| `expert-list` | 高手榜单 |
| `kill-rank` | 绝杀榜 |
| `gallery-link` | 图库入口列表 |

### 成功响应样例

```json
{
  "ok": true,
  "data": [
    {
      "id": 11169,
      "site_id": 5,
      "category": "expert-list",
      "slug": "11169",
      "title": "125期【琴棋书画】已公开",
      "term": "125",
      "href": "/vendor/twcaibawang.com/11169.html",
      "cover_image": null,
      "summary": "香港天天彩第125期琴棋书画资料页",
      "sort_order": 1,
      "status": "published",
      "published_at": "2026-05-22T09:30:00+08:00",
      "updated_at": "2026-05-22T09:32:15+08:00"
    },
    {
      "id": 11170,
      "site_id": 5,
      "category": "expert-list",
      "slug": "11170",
      "title": "125期【平特一肖】已公开",
      "term": "125",
      "href": "/vendor/twcaibawang.com/11170.html",
      "cover_image": null,
      "summary": "香港天天彩第125期平特一肖资料页",
      "sort_order": 2,
      "status": "published",
      "published_at": "2026-05-22T09:31:00+08:00",
      "updated_at": "2026-05-22T09:32:20+08:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 16
  }
}
```

### 空结果样例

```json
{
  "ok": true,
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 0
  }
}
```

## 3. 文章详情接口

用于支撑：

- `11169.html` ~ `11184.html`
- `4873.html` ~ `4879.html`

---

### `GET /api/vendor/articles/{slug}`

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `slug` | string | 是 | 静态页标识，如 `11169`、`4873` |

### Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `site_id` | integer | 是 | 站点 ID，建议固定传 `5` |

### 成功响应样例

```json
{
  "ok": true,
  "data": {
    "id": 11169,
    "site_id": 5,
    "category": "expert-list",
    "slug": "11169",
    "title": "125期【琴棋书画】已公开",
    "term": "125",
    "source_file": "frontend/public/vendor/twcaibawang.com/11169.html",
    "summary": "香港天天彩第125期琴棋书画资料详情",
    "html": "<div class=\"article-body\"><p>125期琴棋书画【画琴书】开???????</p></div>",
    "text": "125期琴棋书画【画琴书】开???????",
    "cover_image": null,
    "related_links": [
      {
        "title": "返回首页",
        "href": "/vendor/twcaibawang.com/"
      },
      {
        "title": "上一条",
        "href": "/vendor/twcaibawang.com/11168.html"
      }
    ],
    "status": "published",
    "published_at": "2026-05-22T09:30:00+08:00",
    "updated_at": "2026-05-22T09:32:15+08:00"
  }
}
```

### 未找到样例

```json
{
  "ok": false,
  "error": "slug=99999 对应文章不存在"
}
```

建议 HTTP 状态码：`404`

## 4. 首页组合型资料块聚合接口

这个接口专门服务首页中“不能直接套单一 `site_prediction_modules`”的块。

首批建议覆盖：

1. `五肖五码`
2. `公开一肖一码`
3. `双波12码`
4. `输尽光`
5. `大小+2头`
6. `天地两肖`

---

### `GET /api/vendor/homepage-modules`

### 用途

一次性返回某个站点首页“组合型资料块”的数据。

### Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `site_id` | integer | 是 | 站点 ID，`twcaibawang` 为 `5` |
| `lottery_type` | integer | 否 | 彩种，未传时按站点默认彩种 |
| `modules` | string | 否 | 逗号分隔模块 key，仅请求部分块，如 `wuxiao_wuma,public_yixiao_yima` |
| `history_limit` | integer | 否 | 每个块返回的历史行数，默认 `8` |

### 建议模块 key

| module_key | 首页块 |
| --- | --- |
| `wuxiao_wuma` | 五肖五码 |
| `public_yixiao_yima` | 公开一肖一码 |
| `shuangbo_12ma` | 双波12码 |
| `shujinguang` | 输尽光 |
| `daxiao_2tou` | 大小+2头 |
| `tiandi_2xiao` | 天地两肖 |

### 顶层成功响应样例

```json
{
  "ok": true,
  "site": {
    "site_id": 5,
    "web_id": 5,
    "site_key": "twcaibawang",
    "lottery_type": 3
  },
  "data": [
    {
      "module_key": "wuxiao_wuma",
      "title": "五肖五码",
      "display_style": "table-composite",
      "history": []
    },
    {
      "module_key": "public_yixiao_yima",
      "title": "公开一肖一码",
      "display_style": "card-composite",
      "history": []
    }
  ]
}
```

## 5. 组合型块详细数据结构

下面定义每个新块建议返回的数据结构和样例。

### 5.1 `wuxiao_wuma` 五肖五码

### 结构说明

一个历史项包含：

- 五肖/四肖/三肖/二肖
- 五码/四码/三码/二码
- 开奖结果

### 单条 history 样例

```json
{
  "issue": "125期",
  "year": "2026",
  "term": "125",
  "groups": {
    "xiao_5": ["狗", "猪", "鸡", "兔", "蛇"],
    "xiao_4": ["狗", "猪", "鸡", "兔"],
    "xiao_3": ["狗", "猪", "鸡"],
    "xiao_2": ["狗", "猪"],
    "code_5": ["11", "22", "31", "38", "44"],
    "code_4": ["11", "22", "31", "38"],
    "code_3": ["11", "22", "31"],
    "code_2": ["11", "22"]
  },
  "result": {
    "res_code": "22",
    "res_sx": "鸡",
    "result_text": "开22鸡"
  },
  "is_opened": false,
  "is_correct": null,
  "raw": {
    "source_mode_ids": [48, 47, 69]
  }
}
```

### 5.2 `public_yixiao_yima` 公开一肖一码

### 单条 history 样例

```json
{
  "issue": "125期",
  "year": "2026",
  "term": "125",
  "xiao_groups": {
    "xiao_9": ["鸡", "虎", "羊", "兔", "狗", "猴", "鼠", "马", "蛇"],
    "xiao_7": ["鸡", "虎", "羊", "兔", "狗", "猴", "鼠"],
    "xiao_5": ["鸡", "虎", "羊", "兔", "狗"],
    "xiao_3": ["鸡", "虎", "羊"]
  },
  "code_groups": {
    "code_14": ["22", "10", "03", "21", "27", "15", "12", "31", "04", "29", "33", "42", "08", "46"],
    "code_8": ["22", "10", "03", "21", "27", "15", "12", "31"],
    "code_5": ["22", "10", "03", "21", "27"]
  },
  "best_pick": {
    "xiao": "鸡",
    "code": "22",
    "text": "本期推荐一肖一码:(鸡22)"
  },
  "result": {
    "res_code": "22",
    "res_sx": "鸡",
    "result_text": "开22鸡"
  },
  "is_opened": false,
  "is_correct": null,
  "raw": {
    "source_mode_ids": [49, 44, 151]
  }
}
```

### 5.3 `shuangbo_12ma` 双波12码

### 单条 history 样例

```json
{
  "issue": "125期",
  "year": "2026",
  "term": "125",
  "waves": ["红波", "绿波"],
  "codes": ["01", "07", "13", "19", "23", "29", "35", "40", "45", "46", "48", "49"],
  "display_text": "【双波12码】红波+绿波：01.07.13.19.23.29.35.40.45.46.48.49",
  "result": {
    "res_code": "22",
    "res_sx": "鸡",
    "result_text": "开22鸡"
  },
  "is_opened": false,
  "is_correct": null
}
```

### 5.4 `shujinguang` 输尽光

### 单条 history 样例

```json
{
  "issue": "125期",
  "year": "2026",
  "term": "125",
  "kill_pairs": ["猴", "猪"],
  "display_text": "125期本期【猴.猪】输尽光",
  "result": {
    "res_code": "22",
    "res_sx": "鸡",
    "result_text": "开22鸡"
  },
  "is_opened": false,
  "is_correct": null
}
```

### 5.5 `daxiao_2tou` 大小+2头

### 单条 history 样例

```json
{
  "issue": "125期",
  "year": "2026",
  "term": "125",
  "size_label": "小数",
  "head_labels": ["1头", "3头"],
  "display_text": "125期【小数 + 1头 + 3头】",
  "result": {
    "res_code": "22",
    "res_sx": "鸡",
    "result_text": "开22鸡"
  },
  "is_opened": false,
  "is_correct": null
}
```

### 5.6 `tiandi_2xiao` 天地两肖

### 单条 history 样例

```json
{
  "issue": "125期",
  "year": "2026",
  "term": "125",
  "tiandi_label": "地肖",
  "pair_xiao": ["牛", "猴"],
  "display_text": "125期天地肖【地肖+牛猴】",
  "result": {
    "res_code": "22",
    "res_sx": "鸡",
    "result_text": "开22鸡"
  },
  "is_opened": false,
  "is_correct": null
}
```

## 6. 组合型模块完整响应样例

下面给一个完整的 `GET /api/vendor/homepage-modules?site_id=5&modules=wuxiao_wuma,public_yixiao_yima&history_limit=2` 返回样例：

```json
{
  "ok": true,
  "site": {
    "site_id": 5,
    "web_id": 5,
    "site_key": "twcaibawang",
    "lottery_type": 3
  },
  "data": [
    {
      "module_key": "wuxiao_wuma",
      "title": "五肖五码",
      "display_style": "table-composite",
      "history": [
        {
          "issue": "125期",
          "year": "2026",
          "term": "125",
          "groups": {
            "xiao_5": ["狗", "猪", "鸡", "兔", "蛇"],
            "xiao_4": ["狗", "猪", "鸡", "兔"],
            "xiao_3": ["狗", "猪", "鸡"],
            "xiao_2": ["狗", "猪"],
            "code_5": ["11", "22", "31", "38", "44"],
            "code_4": ["11", "22", "31", "38"],
            "code_3": ["11", "22", "31"],
            "code_2": ["11", "22"]
          },
          "result": {
            "res_code": "22",
            "res_sx": "鸡",
            "result_text": "开22鸡"
          },
          "is_opened": false,
          "is_correct": null
        },
        {
          "issue": "124期",
          "year": "2026",
          "term": "124",
          "groups": {
            "xiao_5": ["狗", "猪", "羊", "龙", "虎"],
            "xiao_4": ["狗", "猪", "羊", "龙"],
            "xiao_3": ["狗", "猪", "羊"],
            "xiao_2": ["狗", "猪"],
            "code_5": ["17", "24", "31", "42", "49"],
            "code_4": ["17", "24", "31", "42"],
            "code_3": ["17", "24", "31"],
            "code_2": ["17", "24"]
          },
          "result": {
            "res_code": "17",
            "res_sx": "虎",
            "result_text": "开17虎"
          },
          "is_opened": true,
          "is_correct": true
        }
      ]
    },
    {
      "module_key": "public_yixiao_yima",
      "title": "公开一肖一码",
      "display_style": "card-composite",
      "history": [
        {
          "issue": "125期",
          "year": "2026",
          "term": "125",
          "xiao_groups": {
            "xiao_9": ["鸡", "虎", "羊", "兔", "狗", "猴", "鼠", "马", "蛇"],
            "xiao_7": ["鸡", "虎", "羊", "兔", "狗", "猴", "鼠"],
            "xiao_5": ["鸡", "虎", "羊", "兔", "狗"],
            "xiao_3": ["鸡", "虎", "羊"]
          },
          "code_groups": {
            "code_14": ["22", "10", "03", "21", "27", "15", "12", "31", "04", "29", "33", "42", "08", "46"],
            "code_8": ["22", "10", "03", "21", "27", "15", "12", "31"],
            "code_5": ["22", "10", "03", "21", "27"]
          },
          "best_pick": {
            "xiao": "鸡",
            "code": "22",
            "text": "本期推荐一肖一码:(鸡22)"
          },
          "result": {
            "res_code": "22",
            "res_sx": "鸡",
            "result_text": "开22鸡"
          },
          "is_opened": false,
          "is_correct": null
        }
      ]
    }
  ]
}
```

## 7. 推荐实现顺序

建议按这个顺序开发：

1. `GET /api/vendor/articles`
2. `GET /api/vendor/articles/{slug}`
3. `GET /api/vendor/homepage-modules`
4. 先只实现：
   - `wuxiao_wuma`
   - `public_yixiao_yima`
5. 再逐步补：
   - `shuangbo_12ma`
   - `shujinguang`
   - `daxiao_2tou`
   - `tiandi_2xiao`

## 8. 当前明确需要你后端确认的点

在真正开做前，建议你确认这几项：

1. 文章内容是否准备入库，还是先从 vendor 静态 HTML 读取后转 API
2. `高手榜单`、`绝杀榜` 是否需要后台可编辑
3. `五肖五码`、`公开一肖一码` 是否允许由多个现有 mode 聚合生成，而不是强制对应单一 mode_id
4. `输尽光`、`双波12码`、`天地两肖` 是否数据库里已有历史来源表

如果你确认，我下一步可以继续直接补一份“后端表结构建议 + 路由落地清单”。 

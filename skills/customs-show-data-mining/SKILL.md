---
name: customs-show-data-mining
title: Customs & Show Data Mining — 海关数据反查 + 海外展会挖客
description: 海关数据反查进口商 + 三维筛选 + 深挖联系人。支持展会参展商名录挖掘。输入产品词或HS Code→查进口商→筛选→挖人。
triggers:
  - "海关数据"
  - "竞品挖客"
  - "展会找客户"
  - "进口商"
  - "competitor intel"
  - "trade show"
  - "参展商名录"
---

# Customs & Show Data Mining — 海关数据 + 展会挖客

两套挖客方法：海关数据反查进口商 + 海外展会参展商名录挖掘。

---

## 方法一：海关数据反查进口商

### 查询入口

用海关数据查询工具搜索：
- 输入产品英文关键词（如 `precision steel strip`）
- 或输入 HS Code（如 `7226`）
- 选择目标国家

### 三维筛选

**第一维：最近是否有采购记录**
- 90天内有进口 → 高优先级
- 6个月内 → 中优先级
- 超过6个月未进口 → 可能已换供应商

**第二维：采购频率是否稳定**
- 每月进口 → 稳定大客户，P0
- 每季度 → 稳定中型客户，P1
- 偶尔 → 试单性质，P2
- 无规律 → 间歇性需求，P3

**第三维：采购量是否匹配产能**
- 匹配度20%-80%最理想
- 过大需评估产能，过小不优先

### 找到公司后的三层深挖

**第一层：公司基本信息**
```
"{公司名}" company overview
site:{官网} about OR company OR profile
```

**第二层：找关键联系人**
```
site:linkedin.com/in "{公司名}" procurement OR purchasing
site:linkedin.com/in "{公司名}" CEO OR "managing director"
"{公司名}" "@{域名}" email
```

**第三层：交叉验证**
```
"{公司名}" LinkedIn company size
"{公司名}" China supplier OR import from China
```

### 输出格式（海关数据）

```json
{
  "company": "进口商名称",
  "country": "国家",
  "hs_codes": ["进口HS编码"],
  "screening": {
    "last_import_date": "最近进口日期",
    "frequency": "每月/每季/偶尔",
    "priority": "P0/P1/P2/P3"
  },
  "deep_dive": {
    "website": "官网",
    "linkedin": "LinkedIn公司页",
    "key_contacts": [],
    "has_china_supplier": true/false
  }
}
```

---

## 方法二：海外展会参展商名录挖掘

### 为什么用展会

很多海外工厂不投Google广告，但在行业展会一定会出现。展会官网公开的参展商名单就是按行业精准分类的潜在客户名录。

### 找目标展会

```
"{产品}" trade show OR exhibition {年份} {国家}
"{产品}" trade fair exhibitor list
"{行业}" exhibition {国家} {年份}
```

### 展会官网操作步骤

**Step 1** — 找参展商列表入口
- Exhibitor List / Exhibitor Directory
- Brands / Exhibiting Brands
- Show Sectors / Product Categories
- Floor Plan / Hall Plan

**Step 2** — 按行业分类筛选

**Step 3** — 逐家提取信息
- 公司名 + 国家
- 主营产品描述
- 官网链接
- 社交媒体主页
- 展位号

**Step 4** — 深挖联系人
```
"{公司名}" "{展会名}" exhibitor
site:linkedin.com/in "{公司名}" manager OR director
"{公司名}" email contact
```

### 输出格式（展会数据）

```json
{
  "company": "参展商名称",
  "country": "国家",
  "exhibition": "展会名称",
  "booth": "展位号",
  "product_match": "匹配的产品线",
  "website": "官网",
  "contacts_found": [],
  "confidence": "high/medium/low"
}
```

---

## 两渠道对比

| | 海关数据 | 展会名录 |
|------|---------|---------|
| 优势 | 真实交易记录、有采购量 | 公司主动展示、信息完整 |
| 劣势 | 可能延迟、缺少联系方式 | 看不出采购量 |
| 适合 | 找已在进口的买家 | 找新潜在市场 |

---

## 执行流程

```
输入：产品关键词 / HS Code
  │
  ├──→ 海关数据：三维筛选 → 深挖联系人 → 验证
  │
  ├──→ 展会挖掘：搜展会官网 → 找参展商列表 → 提取信息 → 挖联系人
  │
  └──→ 合并去重 → 评分排序 → 输出
```

---
name: b2b-search-keywords
title: B2B 搜索关键词生成器
description: 输入产品品类或HS Code，自动拆分细分品类，生成Google/B2B平台搜索关键词矩阵，直接复制去搜索目标客户。
triggers:
  - "帮我生成搜索关键词"
  - "找客户关键词"
  - "搜索关键词怎么搜"
  - "帮我查HS Code"
  - "生成外贸搜索词"
  - "B2B关键词"
  - "客户搜索词"
category: business
---

# B2B 搜索关键词生成器

输入产品品类 → 拆分子品类 → 查 HS Code → 输出可复制的搜索关键词矩阵。

## 📌 功能边界

| ✅ 做 | ❌ 不做 |
|-------|--------|
| 拆分子品类 | 实际搜索客户 |
| 查 HS Code | 写开发信 |
| 生成搜索关键词 | 市场调研报告 |
| 输出可复制的搜索模板 | 客户跟进 |

## 🔧 执行流程

### Step 1 — 收集输入

问用户三要素：
> 1. 你做什么产品？（如：轴承、灯具、太阳能监控）
> 2. 有没有已知的 HS Code？（选填）
> 3. 目标市场是哪里？（如：中东、欧洲、东南亚、全球）

### Step 2 — 查 HS Code + 拆分子品类

**复合产品**（如"太阳能摄像头"=太阳能板+摄像头）必须分别查各组件。

**HS Code 查询方法：**
1. 打开 https://www.hsbianma.com
2. 搜索框输入中文产品名 → 查询
3. 过滤掉 [过期] 编码，优先选名称匹配 + 退税率高的
4. 复合产品，重复搜第二个组件

**拆分方式：**
- **方式A：大品类**（如"轴承"）→ 查 HS Code → AI 拆子品类 → 输出品类树
- **方式B：有 HS Code**（如"8482"）→ 反查品名 → 列细分产品
- **方式C：细分产品**（如"深沟球轴承"）→ 查 HS Code → 判断复合性 → 进入 Step 3

### Step 3 — 生成关键词矩阵

| 类型 | 说明 | 示例 |
|------|------|------|
| 产品词 | 产品英文名 + supplier/manufacturer | "ball bearing" supplier |
| 买家词 | 产品 + importer/distributor/wholesaler | ball bearing importer |
| 市场词 | 产品 + 目标市场 | ball bearing Dubai wholesale |
| HS Code词 | HS Code + import/buyer/trade | HS 8482.10 import data |
| 平台词 | site: + 平台域名 | site:alibaba.com ball bearing UAE |

### Step 4 — 输出格式

```markdown
# 🎯 搜索关键词包：[产品中文名称]

## 一、产品品类树
| 总品类 | 子品类 | 具体产品 |

## 二、HS Code（关键编码）
| HS Code | 品名 | 退税率 |

## 三、关键词矩阵
### 🔹 产品词（直接搜索供应商）
### 🔹 买家词（找采购商）
### 🔹 B2B平台搜索词
### 🔹 地区市场词
（按目标市场分节，全球时包含中东/欧洲/东南亚/南美/非洲/澳洲）

## 四、Google 直接搜索模板
```

## 🔧 关键词生成公式

```
[产品英文词] + [买家类型词] + [市场地域词] + [HS Code] + [搜索语法]
```

### 买家类型词表
```
importer / distributor / wholesaler / dealer /
trading company / agent / supplier / procurement
```

### 市场地域词表
```
中东：Dubai / UAE / Saudi Arabia / Middle East / Gulf states
欧洲：Germany / UK / Europe / EU
东南亚：Vietnam / Indonesia / Thailand / Southeast Asia
南美：Brazil / Mexico / Latin America
非洲：Africa / Nigeria / South Africa
澳洲：Australia / New Zealand
```

### Google 搜索语法
```
精准搜索："{产品}" "{买家类型}" {市场}
LinkedIn：site:linkedin.com/in "{行业}" "purchasing" "{市场}"
B2B平台：site:alibaba.com "{产品}" "{市场}"
展会："{产品}" "trade show" "{市场}" 2025
```

## 📊 参考：常见行业品类拆分

### 轴承（HS 8482）
├── 深沟球轴承 → 8482.10
├── 调心球轴承 → 8482.10
├── 圆锥滚子轴承 → 8482.20
├── 圆柱滚子轴承 → 8482.50
└── 滚针轴承 → 8482.40

### 灯具（HS 9405）
├── 吊灯 → 9405.11
├── 壁灯/吸顶灯 → 9405.19
├── 台灯/落地灯 → 9405.20
├── LED灯 → 9405.40
└── 灯具零件 → 9405.99

### 家具（HS 9401-9403）
├── 座椅 → 9401
├── 办公家具 → 9403
└── 木家具 → 9403.40

### 阀门（HS 8481）
├── 球阀 → 8481.10
├── 止回阀 → 8481.30
├── 安全阀 → 8481.40
└── 龙头 → 8481.80

### 五金工具（HS 8205-8207）
├── 手工工具 → 8205
├── 电动工具 → 8467
└── 紧固件 → 7318

### 监控摄像头（HS 8525.8x）
├── 网络摄像头 → 8525.81
├── 监控摄像头 → 8525.89
└── 太阳能板配件 → 8541.42

## ⚠️ 注意事项

- HS Code 建议报关行确认，AI 仅供参考
- 前6位全球通用，后几位各国不同
- 关键词需要根据实际搜索结果微调
- 复合产品（太阳能摄像头等）分别查各组件 HS Code

## ✅ 输出后建议

1. "挑一个关键词去 Google 搜一下，看结果是否精准"
2. "需要存到 CRM 或其他地方吗？"
3. "找到目标公司后，可以交给另一个 Agent 做验证"

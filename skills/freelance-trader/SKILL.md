---
name: freelance-trader
title: Freelance Trader - 多语言关键词生成器
description: 输入产品品类或HS Code，自动拆分细分品类，按地区/语言/叫法生成多层搜索关键词矩阵。关键词不够时自动扩展加深。
triggers:
  - "生成关键词"
  - "找客户"
  - "搜索词"
  - "B2B关键词"
  - "多语言关键词"
---

# Freelance Trader — 多语言关键词生成器

输入产品品类 → 拆分品类树 → 按目标市场生成**多语言、多叫法、多层级**的关键词矩阵。

---

## 功能边界

| 做 | 不做 |
|-------|--------|
| 拆分子品类 | 实际搜索客户 |
| 生成多语言关键词（本地语+英语） | 写开发信 |
| 按地区适配不同叫法 | 市场调研报告 |
| 关键词不够时自动扩展加深 | 客户背调 |
| 输出可直接复制的搜索模板 | |

---

## 核心原则：关键词必须分地区、分语言、分叫法

同一个产品在不同国家叫法完全不同。只搜英语关键词会漏掉大量本地买家。

**例：精密钢带**
| 地区 | 当地叫法 | 搜索关键词 |
|------|---------|-----------|
| 台湾/日本 | 精密鋼帶 / 精密帯鋼 | "精密鋼帶" メーカー / "精密帯鋼" 輸入 |
| 越南 | thép cuộn cán nguội / thép băng | "thép băng" nhập khẩu / "thép cuộn" mua |
| 墨西哥 | fleje de acero / cinta de acero | "fleje de acero" importador / "cinta de acero" proveedor |
| 德国 | Präzisionsbandstahl / Kaltband | "Präzisionsbandstahl" Einkauf / "Kaltband" Importeur |
| 中东 | steel strip / صلب | "steel strip" Dubai importer / "شريط الصلب" مستورد |

---

## 执行流程

### Step 1 — 收集输入

1. 做什么产品？（品类+牌号+规格）
2. 目标市场是哪些？（国家/地区）
3. 客户类型偏好？（终端工厂 / 分销商 / 进口商）

### Step 2 — 查 HS Code + 拆分子品类

**HS Code 查询：** https://www.hsbianma.com
- 输入产品中文名 → 查询
- 过滤[过期]编码，优先选退税率高、名称精确匹配的
- 前6位全球通用，后几位按国别不同

**复合产品必须拆分组件：** 如"太阳能摄像头"=太阳能板+摄像头，分别查。

**拆分子品类：**
- 方式A：大品类（如"轴承"）→ 查HS Code → 拆子品类
- 方式B：已有HS Code → 反查品名 → 列细分
- 方式C：细分产品 → 查HS Code → 判断复合性

**Output:**
| HS Code | 品名 | 退税率 | 适用地区 |
|---------|------|--------|---------|

### Step 3 — 按地区生成关键词（核心）

#### 第一层：英语通用词（10-15个）
```
"{product}" + importer / buyer / distributor / procurement / sourcing
"{product}" + manufacturer / supplier / factory
"{product}" + "import data" / "trade data" / "shipment"
```

#### 第二层：本地语言关键词（每个市场 5-10个）
```
# 日语
"{product}" 輸入 / 仕入れ / 調達 / メーカー

# 越南语
"{product}" nhập khẩu / mua hàng / nhà cung cấp / tìm kiếm

# 西班牙语（拉美）
"{product}" importador / comprador / distribuidor / proveedor

# 德语
"{product}" Importeur / Einkauf / Lieferant / Beschaffung

# 阿拉伯语（中东）
"{product}" مستورد / مشتري / مورد / بحث

# 法语、葡萄牙语、韩语、俄语、土耳其语、印尼语、泰语 — 同理
```

#### 第三层：牌号/标准精准搜索（5-10个）
```
"SK5" OR "SK4" steel strip {country}
"65Mn" cold rolled strip buyer
"JIS standard" steel strip importer {country}
"ASTM" steel strip buyer {country}
"DIN" precision steel strip procurement
```

#### 第四层：行业用途词（5个）
```
"spring manufacturer" steel strip {country}
"bearing manufacturer" steel buyer
"automotive stamping" steel strip buyer {country}
```

#### 第五层：平台 + 展会词（5-10个）
```
site:linkedin.com/company "steel" "procurement" {country}
site:kompass.com "steel strip" {country}
site:europages.com "precision steel" importer
"{product}" "trade show" OR "exhibition" {year}
```

### Step 4 — 关键词不够时的扩展规则

1. **变体扩展**：全称vs缩写、单数vs复数、连字符变体
2. **同义词替换**：importer → buyer / purchaser / procurement manager
3. **地域细分**：国家级 → 城市级（Dubai → Dubai/Abu Dhabi/Sharjah）
4. **行业树深入**：大类→细分→具体产品
5. **上下游扩展**：向下游终端工厂、向上游原材料供应商
6. **搜索语法变体**：普通搜索、site定向、filetype定向、intitle定向、inurl定向

---

## 语言→买家词映射表

| 语言 | 进口商 | 买家 | 分销商 | 供应商 | 采购 | 搜索 |
|------|--------|------|--------|--------|------|------|
| 日语 | 輸入業者 | バイヤー | 販売代理店 | サプライヤー | 調達 | 検索 |
| 越南语 | nhà nhập khẩu | người mua | nhà phân phối | nhà cung cấp | mua hàng | tìm kiếm |
| 西班牙语 | importador | comprador | distribuidor | proveedor | compras | buscar |
| 德语 | Importeur | Käufer | Händler | Lieferant | Beschaffung | Suche |
| 法语 | importateur | acheteur | distributeur | fournisseur | approvisionnement | recherche |
| 葡萄牙语 | importador | comprador | distribuidor | fornecedor | compras | pesquisa |
| 韩语 | 수입업체 | 구매자 | 유통업체 | 공급업체 | 구매 | 검색 |
| 阿拉伯语 | مستورد | مشتري | موزع | مورد | شراء | بحث |
| 俄语 | импортер | покупатель | дистрибьютор | поставщик | закупки | поиск |
| 土耳其语 | ithalatçı | alıcı | distribütör | tedarikçi | satın alma | arama |
| 印尼语 | importir | pembeli | distributor | pemasok | pembelian | cari |
| 泰语 | ผู้นำเข้า | ผู้ซื้อ | ผู้จัดจำหน่าย | ผู้จัดหา | จัดซื้อ | ค้นหา |

---

## 注意事项

- HS Code 前6位全球通用，后几位按国别不同，建议报关行确认
- 本地语关键词优先用目标市场的主流搜索引擎（越南cococ.com，俄罗斯yandex.ru）
- 每个市场至少生成30个不同维度/语言的关键词才算覆盖充分

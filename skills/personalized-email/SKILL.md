---
name: personalized-email
description: 输入客户网址 + 企业信息，生成一对一个性化开发信。包含客户背调、企业优势匹配、工程案例背书的完整闭环。
trigger: "客户网址 + 企业信息"
---

# Personalized Development Email Skill

## 触发条件
用户输入：客户网站地址 + 企业信息（含工程案例）
目标：生成一对一个性化开发信

---

## 用户需准备的内容

### A. 企业基础信息
```
企业名称：
英文名称：
成立年份：
员工人数：
工厂面积：
主营产品/服务：
核心优势（最多3条）：
出口经验地区：
资质认证：
英文介绍（可选，200字以内）：
```

### B. 工程案例库（可填多条，AI 自动匹配最相关的）
```
案例1：
- 客户行业：
- 客户地区：
- 用我们的产品做什么：
- 我们解决了什么问题：
- 结果/客户反馈：

案例2：（同上格式，可填多条）
```

---

## 执行流程

### 第一步：客户背调
收到客户网址后，自动抓取：
- 对方公司名称、主营业务、产品线
- 目标市场、主要客户群体
- 公司规模、成立时间（若有）
- 社交媒体 LinkedIn 信息（若有）
- 对方在售产品的特点和市场定位

### 第二步：信息分析
将背调结果与用户企业信息对比：
- 匹配相同行业 → 找对应工程案例
- 匹配相似产品 → 突出相关经验
- 匹配目标市场 → 突出出口地区经验
- 找出对方痛点 → 对应自己的优势

### 第三步：生成个性化开发信
输出内容包含：
1. 客户背调摘要（1-2句，确认理解对方业务）
2. 匹配依据说明（哪个案例、哪条优势相关）
3. 个性化开发信正文

---

## 开发信结构

**标题：** 突出对方业务关键词，不出现产品型号

**第一段（开篇）：**
提对方正在做的事，或对方行业的痛点
> "I noticed your company specializes in [客户主营业务]..."

**第二段（信任建立）：**
用真实工程案例做背书，只说事实和数据
> "We've helped [同类客户] solve [具体问题]..."

**第三段（价值传递）：**
对应对方痛点，提自己的核心优势
> "Our [优势] can help you [具体好处]..."

**第四段（行动号召）：**
具体下一步动作，不要只说"欢迎咨询"
> "Would you be open to a 15-minute call this week?"

---

## 输出示例

```
【客户背调摘要】
公司：ABC Mining Equipment
主营业务：矿山机械配件制造
目标市场：南非、赞比亚
主要产品：液压缸、履带配件

【匹配依据】
✅ 匹配客户行业：矿山机械 → 使用案例1
✅ 匹配目标市场：南非 → 有非洲出口经验
✅ 匹配产品线：履带配件 → 我方底盘件经验

【个性化开发信】

Subject: Helping [ABC] Reduce Downtime in Zambia Mining Operations

Dear [Name],

I noticed your company supplies hydraulic cylinders and undercarriage parts to mining operations across Zambia and South Africa. We've helped similar mining companies in South Africa reduce equipment downtime by 30% through our reliable undercarriage parts supply...

[正文内容...]

Best regards,
[用户企业名称]
```

---

## 注意事项
- 若客户网址无法访问或信息极少，告知用户并提供默认模板
- 案例匹配时，优先选：同行业 > 同产品线 > 同地区
- 开发信语气根据对方公司规模调整（小公司偏亲和，大公司偏专业）
- 生成后用户可自行修改再发送

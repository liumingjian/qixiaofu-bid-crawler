# Story 02: 招标信息提取模块

**Story ID**: STORY-02
**关联任务**: Task 2.1
**优先级**: 🔴 P0 - 最高（最关键）
**预计时长**: 3小时
**负责人**: -
**状态**: ✅ 已完成
**依赖**: STORY-01

---

## 📋 Story描述

作为系统核心模块，我需要实现一个招标信息提取器，使用正则表达式从公众号文章文本中自动提取结构化的招标信息，包括项目名称、预算金额、采购人、获取文件时间等关键字段。

---

## 🎯 验收标准

- [x] 使用现有`wechat_article.json`测试，提取准确率≥95%
- [x] 能正确识别文章中的4个招标项目
- [x] 必填字段(项目名称、预算、采购人、获取文件时间)提取完整
- [x] 可选字段(项目编号、服务期限、采购内容)尽量提取
- [x] 生成唯一ID，支持去重
- [x] 不符合规则的项目不保存(验证逻辑)

---

## ✅ TODO清单

### 1. 创建数据模型 (15分钟)
- [x] 创建 `core/bid_extractor.py` 文件
- [x] 定义招标信息数据结构:
  ```python
  BidInfo = {
      "id": str,  # MD5(项目名称+采购人)
      "project_name": str,  # 必填
      "budget": str,  # 必填
      "purchaser": str,  # 必填
      "doc_time": str,  # 必填
      "project_number": str,  # 可选
      "service_period": str,  # 可选
      "content": str,  # 可选
      "source_url": str,
      "source_title": str,
      "extracted_time": str,  # ISO格式
      "status": str  # new/notified/archived
  }
  ```
- [x] 添加类型注解

**验证**: 数据结构清晰完整

---

### 2. 定义正则表达式模式 (30分钟)
- [x] 创建 `BidInfoExtractor` 类
- [x] 定义正则表达式字典 `PATTERNS`
  - [x] 项目名称、预算、采购人等字段匹配公式
- [x] 添加正则表达式注释说明

**验证**: 每个正则都用示例文本测试通过

---

### 3. 实现项目块分割逻辑 (30分钟)
- [x] 实现 `_split_projects()` 方法
- [x] 识别项目分隔符: "1项目名称"、"2项目名称"、"3项目名称"、"4项目名称"
- [x] 正则模式: `r'(\d+)项目名称'`
- [x] 使用 `re.split()` / `finditer()` 分割文本
- [x] 处理分割后的列表，组合序号和内容
- [x] 处理边界情况:
  - [x] 文章中没有项目(返回空列表)
  - [x] 只有1个项目
  - [x] 项目编号不连续

**代码示例**:
```python
def _split_projects(self, text: str) -> List[str]:
    """按序号分割项目块"""
    # 匹配 1项目名称、2项目名称...
    pattern = r'(\d+)项目名称'
    parts = re.split(pattern, text)

    # parts结构: ['前言', '1', '项目1内容', '2', '项目2内容', ...]
    blocks = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            blocks.append(parts[i + 1])

    return blocks
```

**验证**:
- 测试现有文章，确认分割出4个项目块
- 打印每个块的前50字符，确认内容正确

---

### 4. 实现字段提取逻辑 (45分钟)
- [x] 实现 `extract_from_text()` 主方法
- [x] 调用 `_split_projects()` 分割项目
- [x] 遍历每个项目块:
  - [x] 对每个字段使用正则提取
  - [x] 提取成功则去除首尾空格
  - [x] 提取失败则设为空字符串或None
- [x] 收集所有提取的招标信息
- [x] 返回招标信息列表

**代码示例**:
```python
def extract_from_text(self, text: str, article_meta: dict) -> List[dict]:
    """从文章文本提取招标信息"""
    bids = []
    project_blocks = self._split_projects(text)

    for block in project_blocks:
        bid = {}

        # 提取各字段
        for field, pattern in self.PATTERNS.items():
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                bid[field] = match.group(1).strip()
            else:
                bid[field] = ""

        # 验证必填字段
        if self._validate_required_fields(bid):
            # 生成唯一ID
            bid['id'] = self._generate_id(bid)

            # 添加元数据
            bid['source_url'] = article_meta.get('url', '')
            bid['source_title'] = article_meta.get('title', '')
            bid['extracted_time'] = datetime.now().isoformat()
            bid['status'] = 'new'

            bids.append(bid)

    return bids
```

**验证**: 提取的字段值正确

---

### 5. 实现字段验证逻辑 (20分钟)
- [x] 实现 `_validate_required_fields()` 方法
- [x] 验证必填字段非空:
  - [x] `project_name`
  - [x] `budget`
  - [x] `purchaser`
  - [x] `doc_time`
- [x] 添加字段格式验证:
  - [x] 预算金额包含"元"
  - [x] 项目名称长度 ≥ 5个字符
- [x] 返回布尔值

**代码示例**:
```python
def _validate_required_fields(self, bid: dict) -> bool:
    """验证必填字段"""
    required_fields = ['project_name', 'budget', 'purchaser', 'doc_time']

    for field in required_fields:
        if not bid.get(field) or not bid[field].strip():
            self.logger.warning(f"Missing required field: {field}")
            return False

    # 格式验证
    if '元' not in bid['budget']:
        self.logger.warning(f"Invalid budget format: {bid['budget']}")
        return False

    if len(bid['project_name']) < 5:
        self.logger.warning(f"Project name too short: {bid['project_name']}")
        return False

    return True
```

**验证**:
- 测试缺少字段的情况
- 测试格式错误的情况

---

### 6. 实现唯一ID生成 (15分钟)
- [x] 实现 `_generate_id()` 方法
- [x] 使用 `项目名称 + 采购人` 生成唯一标识
- [x] 使用MD5哈希
- [x] 返回16位十六进制字符串

**代码示例**:
```python
import hashlib

def _generate_id(self, bid: dict) -> str:
    """生成唯一ID"""
    unique_str = f"{bid['project_name']}{bid['purchaser']}"
    hash_obj = hashlib.md5(unique_str.encode('utf-8'))
    return hash_obj.hexdigest()[:16]
```

**验证**:
- 相同项目名称+采购人生成相同ID
- 不同项目生成不同ID

---

### 7. 添加日志记录 (10分钟)
- [x] 在 `__init__()` 中初始化logger
- [x] 在关键步骤添加日志:
  - [x] 分割项目块: `logger.info(...)`
  - [x] 字段提取: `logger.debug(...)`
  - [x] 验证失败: `logger.warning(...)`
  - [x] 提取成功: `logger.info(...)`

**验证**: 日志输出清晰，便于调试

---

### 8. 编写单元测试 (30分钟)
- [x] 创建 `tests/test_bid_extractor.py` 文件
- [x] 测试用例1: 测试项目分割
  - [x] 输入: 包含4个项目的文本
  - [x] 输出: 4个项目块
- [x] 测试用例2: 测试必填字段提取
  - [x] 验证项目名称、预算、采购人、文件时间
- [x] 测试用例3: 测试可选字段提取
  - [x] 验证项目编号、服务期限、采购内容
- [x] 测试用例4: 测试字段验证
  - [x] 缺少必填字段返回False
  - [x] 完整字段返回True
- [x] 测试用例5: 测试ID生成
  - [x] 相同输入生成相同ID
- [x] 测试用例6: 使用真实文章测试
  - [x] 读取 `wechat_article.json`
  - [x] 提取招标信息
  - [x] 验证数量和准确性

**代码示例**:
```python
import unittest
import json
from core.bid_extractor import BidInfoExtractor

class TestBidExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = BidInfoExtractor()

    def test_split_projects(self):
        text = "1项目名称：项目A\n2项目名称：项目B"
        blocks = self.extractor._split_projects(text)
        self.assertEqual(len(blocks), 2)

    def test_extract_with_real_article(self):
        with open('wechat_article.json', 'r', encoding='utf-8') as f:
            article = json.load(f)

        bids = self.extractor.extract_from_text(
            article['content_text'],
            {'url': article.get('url', ''), 'title': article.get('title', '')}
        )

        self.assertEqual(len(bids), 4)  # 应该提取4个项目
        self.assertGreater(len(bids[0]['project_name']), 0)
        self.assertIn('元', bids[0]['budget'])
```

**验证**: 所有测试用例通过

---

## 📦 交付物

- [x] `core/bid_extractor.py` - 招标信息提取类
- [x] `tests/test_bid_extractor.py` - 单元测试
- [x] 测试报告 - 使用真实文章的提取结果

---

## 🧪 测试清单

使用 `wechat_article.json` 进行完整测试:

- [x] 提取项目数量 = 4
- [x] 项目1: "内蒙古科技大学数据中心IT机房专用精密空调采购项目（二次）"
  - [x] 预算: "97.38万元"
  - [x] 采购人: "内蒙古科技大学"
  - [x] 项目编号: "NMGDG-2025ZB-47"
- [x] 项目2: "宿州学院2025年网络安全运维服务项目"
  - [x] 预算: "9万元"
  - [x] 采购人: "宿州学院"
  - [x] 服务期限: "本项目服务期限为1年"
- [x] 项目3: "桂林银行2025年Oracle数据库维保服务采购项目"
  - [x] 预算: "26万元"
  - [x] 采购人: "桂林银行股份有限公司"
  - [x] 采购内容提取成功
- [x] 项目4: "吕梁市财政局业务网络与硬件设备运维服务项目"
  - [x] 预算: "34.900896万元"
  - [x] 采购人: "吕梁市财政预算审核中心"

---

## 📝 开发笔记

### 正则表达式优化技巧
1. 使用 `[:\\s：]*` 匹配冒号和空格的各种组合
2. 使用 `[^\n]+` 匹配除换行外的所有字符
3. 使用 `re.IGNORECASE` 忽略大小写
4. 使用 `strip()` 去除首尾空格

### 可能遇到的问题
1. **问题**: 正则匹配不到某些字段
   - **解决**: 检查文章中该字段的实际格式，调整正则
   - **调试**: 使用 `re.findall()` 测试正则

2. **问题**: 项目分割不准确
   - **解决**: 打印 `re.split()` 结果，检查分割点
   - **调试**: 手动查看文章中项目序号的格式

3. **问题**: 提取准确率低
   - **解决**: 收集失败case，分析原因，优化正则
   - **调试**: 添加详细日志，记录每个字段的提取结果

---

## ✨ 完成标准

- [x] 运行单元测试全部通过:
```bash
python -m pytest tests/test_bid_extractor.py -v
```
- [x] 使用真实文章测试:
```python
from core.bid_extractor import BidInfoExtractor
import json

extractor = BidInfoExtractor()
with open('wechat_article.json') as f:
    article = json.load(f)

bids = extractor.extract_from_text(article['content_text'], article)
print(f"Extracted {len(bids)} bids")
for bid in bids:
    print(f"- {bid['project_name']}: {bid['budget']}")
```
- [x] 输出4个招标项目，字段完整

---

## 📅 时间记录

- **开始时间**: 2025-11-25 22:30
- **完成时间**: 2025-11-25 22:45
- **实际耗时**: 0.25小时
- **备注**: 使用 `wechat_article.json` 验证并补齐日志记录/ID生成逻辑。

---

## 🔍 代码审查清单

- [ ] 代码符合PEP 8规范
- [ ] 所有函数有类型注解
- [ ] 所有函数有docstring
- [ ] 正则表达式有注释说明
- [ ] 异常情况有处理
- [ ] 日志记录完整
- [ ] 单元测试覆盖率 ≥ 80%

# 图腾数安招标信息搜集平台 - UI 设计规范

## 1. 色彩系统

### 主色调
```css
--primary-color: #1e40af;        /* 深蓝色 - 主要按钮、链接 */
--primary-hover: #1e3a8a;        /* 深蓝悬停态 */
--primary-light: #3b82f6;        /* 浅蓝色 - 次要元素 */
```

### 中性色
```css
--bg-primary: #ffffff;           /* 主背景 */
--bg-secondary: #f8fafc;         /* 次要背景 */
--bg-tertiary: #f1f5f9;          /* 三级背景 */
--text-primary: #1e293b;         /* 主要文字 */
--text-secondary: #64748b;       /* 次要文字 */
--text-tertiary: #94a3b8;        /* 辅助文字 */
--border-color: #e2e8f0;         /* 边框颜色 */
```

### 功能色
```css
--success-color: #10b981;        /* 成功/金额 */
--warning-color: #f59e0b;        /* 警告/预算 */
--danger-color: #ef4444;         /* 错误/删除 */
--info-color: #3b82f6;           /* 信息提示 */
```

### 侧边栏
```css
--sidebar-bg: #1e293b;           /* 侧边栏背景 */
--sidebar-text: #e2e8f0;         /* 侧边栏文字 */
--sidebar-active: #3b82f6;       /* 侧边栏激活项 */
```

## 2. 字体系统

### 字体族
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", 
             "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
```

### 字号规范
- **H1**: 28px (1.75rem) - 页面主标题
- **H2**: 24px (1.5rem) - 区块标题
- **H3**: 20px (1.25rem) - 卡片标题
- **Body**: 14px (0.875rem) - 正文
- **Small**: 12px (0.75rem) - 辅助文本

### 字重
- **Regular**: 400 - 正文
- **Medium**: 500 - 标题
- **Semibold**: 600 - 强调
- **Bold**: 700 - 重要信息

## 3. 间距系统

使用 8px 基准网格系统：

```css
--spacing-1: 4px;    /* 0.25rem */
--spacing-2: 8px;    /* 0.5rem */
--spacing-3: 12px;   /* 0.75rem */
--spacing-4: 16px;   /* 1rem */
--spacing-6: 24px;   /* 1.5rem */
--spacing-8: 32px;   /* 2rem */
--spacing-12: 48px;  /* 3rem */
```

## 4. 圆角规范

```css
--radius-sm: 6px;    /* 小圆角 - 按钮、输入框 */
--radius-md: 12px;   /* 中圆角 - 卡片 */
--radius-lg: 16px;   /* 大圆角 - 弹窗 */
--radius-full: 9999px; /* 完全圆形 - 徽章 */
```

## 5. 阴影系统

```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
```

## 6. 核心组件规范

### 6.1 按钮

**主要按钮 (Primary)**
- 背景色: `--primary-color`
- 文字色: `#ffffff`
- 高度: 40px
- 圆角: `--radius-sm`
- 内边距: 16px 24px
- 悬停: 背景色变为 `--primary-hover`，添加 `--shadow-md`

**次要按钮 (Secondary)**
- 背景色: 透明
- 边框: 1px solid `--border-color`
- 文字色: `--text-primary`
- 其他同主要按钮

### 6.2 输入框

- 高度: 40px
- 边框: 1px solid `--border-color`
- 圆角: `--radius-sm`
- 内边距: 8px 12px
- 聚焦: 边框色变为 `--primary-color`，添加 0 0 0 3px rgba(59, 130, 246, 0.1) 外发光

### 6.3 卡片

- 背景: `--bg-primary`
- 边框: 1px solid `--border-color`（可选）
- 圆角: `--radius-md`
- 内边距: `--spacing-6`
- 阴影: `--shadow-sm`

### 6.4 表格

- 表头背景: `--bg-secondary`
- 表头文字: `--text-secondary`，字重 600
- 行高: 56px
- 边框: 1px solid `--border-color`
- 悬停行: 背景色 `--bg-tertiary`

### 6.5 徽章 (Badge)

- 高度: 24px
- 内边距: 4px 12px
- 圆角: `--radius-full`
- 字号: 12px
- 根据类型使用不同功能色作为背景

## 7. 布局规范

### 侧边栏
- 宽度: 240px
- 背景: `--sidebar-bg`
- 固定定位

### 顶部导航
- 高度: 64px
- 背景: `--bg-primary`
- 边框底部: 1px solid `--border-color`

### 内容区
- 左侧偏移: 240px（侧边栏宽度）
- 内边距: `--spacing-6` 到 `--spacing-8`

### 详情抽屉
- 宽度: 480px
- 从右侧滑入
- 背景: `--bg-primary`
- 阴影: `--shadow-xl`

## 8. 交互规范

### 过渡动画
```css
transition: all 0.2s ease-in-out;
```

### 加载状态
- 使用旋转动画的 spinner
- 颜色: `--primary-color`
- 尺寸: 24px

### 悬停效果
- 按钮: 轻微提升（translateY -1px）+ 阴影增强
- 列表行: 背景色变化
- 链接: 文字颜色变化 + 下划线

## 9. 响应式断点

```css
--breakpoint-sm: 640px;   /* 移动设备 */
--breakpoint-md: 768px;   /* 平板 */
--breakpoint-lg: 1024px;  /* 桌面 */
--breakpoint-xl: 1280px;  /* 大屏幕 */
```

## 10. 图标规范

- 使用 Bootstrap Icons 或 Phosphor Icons
- 默认尺寸: 20px
- 颜色继承父元素文字颜色
- 与文字间距: 8px

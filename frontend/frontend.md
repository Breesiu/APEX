# Poster Edit Frontend

基于 React + TypeScript + Vite 构建。

## 目录结构

- `src/components/PosterEditPanel.tsx`: 核心编辑组件，包含 PPTX 上传、预览及 AI 编辑交互逻辑。
- `src/api.ts`: 与后端 API 的通信接口。
- `src/App.tsx`: 应用主入口。

## 快速开始

### 1. 环境准备

确保已安装 [Node.js](https://nodejs.org/) (推荐 v16+)。

### 2. 安装依赖

在 `frontend` 目录下运行：

```bash
npm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

默认运行在 `http://localhost:3000` (或 Vite 自动分配的端口)。

### 4. 后端连接

前端默认配置连接到 `http://localhost:8000`。请确保后端服务已启动并运行。

## 功能特性

- **PPTX 上传与预览**: 支持上传本地 PPTX 文件并生成预览图。
- **AI 智能编辑**: 输入文本指令（如"把标题改成红色"），通过后端 AI 代理自动修改海报。
- **实时状态反馈**: 实时显示编辑任务的日志和进度。
- **结果下载**: 下载编辑完成后的 PPTX 文件。

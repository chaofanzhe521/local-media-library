```
media_library/
├── app.py             
├── media_data.db      
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── index.html     
    └── manage.html
```    

# 本地媒体库管理器

这是一个使用 Python Flask 构建的本地媒体文件管理工具。您可以用它来为您的视频、图片、小说等文件添加标签，并方便地进行搜索和浏览。

## ✨ 功能特性

- **标签化管理**：为每个媒体文件添加任意数量的自定义标签。
- **组合筛选**：通过标题、类型和多个标签的组合进行精确搜索。
- **封面预览**：支持为视频或小说自定义封面。
- **Web 界面**：通过浏览器进行所有操作，界面美观，支持拖拽。
- **纯本地化**：所有数据和文件都存储在您自己的电脑上，无需联网。
- **安全退出**：提供明确的退出机制，避免进程残留。

## 🚀 如何运行

### 方式一：直接运行 (推荐)
1. 前往 [Releases 页面](https://github.com/chaofanzhe521/local-media-library/releases/tag/v1.0.0)。
2. 下载并双击 `app.exe` 即可运行。

### 方式二：从源代码运行
1. 确保您已安装 Python 3。
2. 克隆本仓库：`git clone https://github.com/chaofanzhe521/local-media-library.git`
3. 进入项目目录：`cd media_library`
4. 运行主程序：`python app.py`
5. 在浏览器中打开 `http://127.0.0.1:5000`。

## 📝 注意事项
- 本程序仅为个人使用，文件服务功能未做严格的安全校验，请勿在公共网络上部署。
- 本程序在Gemini帮助下完成，无聊时打发时间顺便做了点需要的。

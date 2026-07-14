# README Screenshots

这里存放 Conclusion README 使用的真实运行截图。当前截图来自固定的公开安全 demo 数据库。

## 文件

```text
list.png
detail.png
create.png                 # 新增页面实现后加入
search-and-tags.png        # 搜索和标签筛选实现后加入
```

## 规则

- 只能使用专门构造的公开安全假数据，禁止读取或复制个人生产数据库。
- 使用固定 viewport、固定 demo 数据和 headless Chromium，保证截图可重复生成。
- 优先复用 FengDock 已有的 Playwright 栈，不为截图另加 Selenium。
- 截图必须来自实际运行页面，不使用设计稿、AI 生成图片或手工拼接图冒充产品效果。
- 只有在页面或关键视觉行为发生实质变化时才更新对应图片。
- 截图脚本、demo seed 和 README 图片引用应与第一个 UI 页面在同一个小功能提交中加入。

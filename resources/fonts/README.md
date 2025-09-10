# 字体文件说明

为了正确显示中文界面，需要在此目录下放置一个中文字体文件。

## 推荐字体

1. **Noto Sans CJK** - Google和Adobe合作开发的开源字体
   - 文件名: `NotoSansCJKsc-Regular.otf`
   - 下载地址: https://www.google.com/get/noto/#sans-cjk

2. **思源黑体** - Adobe开发的开源中文字体
   - 文件名: `SourceHanSansSC-Regular.otf`
   - 下载地址: https://github.com/adobe-fonts/source-han-sans

3. **MiSans** - 小米开发的开源中文字体（已包含在项目中）
   - 文件名: `MiSans-Regular.otf` 及其他字重
   - 许可协议: 已包含在字体文件目录中

## 使用方法

1. 下载上述任一字体文件（如果使用MiSans字体，则已包含在项目中）
2. 将字体文件放置在此目录下
3. 重新启动应用程序

应用程序会自动检测并使用以下字体（按优先级顺序）：
1. MiSans-Regular.otf
2. MiSans-Normal.otf
3. MiSans-Medium.otf
4. MiSans-Semibold.otf
5. MiSans-Bold.otf
6. MiSans-Demibold.otf
7. MiSans-Light.otf
8. MiSans-ExtraLight.otf
9. MiSans-Thin.otf
10. MiSans-Heavy.otf
11. NotoSansCJKsc-Regular.otf

## 注意事项

- 字体文件大小约为10-20MB
- 应用程序会自动检测并加载此字体文件
- 如果字体文件不存在，将使用系统默认字体（可能导致中文显示为方块或问号）
- MiSans字体已包含在项目中，遵循其许可协议
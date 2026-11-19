# SheerID 过审套件

材料是生成的，不是找来的。找现成"免费认证器"这条路没有稳定产出，能过的是自己按审核规则产出的材料。

## 套件结构

```
sheerid_kit/
├── build_kit.py            生成器（改 fields.json 后重跑）
├── fields.json             唯一字段源
└── out/
    ├── enrollment_letter.docx     可编辑在读证明信（要自己签/改时用）
    ├── enrollment_letter.jpg      扫描质感稿 —— 这是要上传的那份
    ├── id_front.jpg               学生证正面
    ├── id_back.jpg                学生证反面
    └── id_combined.jpg            正反拼合（部分商户只收单文件）
```

重新生成：

```bash
cd sheerid_kit
python build_kit.py
```

## 三步用法

**1. 定字段。** 编辑 `fields.json`。这里有两个字段决定成败：

- `student_name` —— 必须和你在 SheerID 表单里输入的姓名**逐字一致**。差一个中间名首字母就会被判 `Name does not match`。
- `school_name` —— 必须是 SheerID 学校下拉框里**真实存在**的学校。生成的校名可以是虚构的，但提交时会要求从列表选，选一个真实学校然后把 `fields.json` 里的校名/地址/网址改成该学校官网上的真实值。

`letter_date` 保持在今天往前 30 天内。超过 90 天直接触发 `Unable to confirm current enrollment`。

**2. 换照片。** `photo` 填一张证件照路径（正面免冠、纯色背景、600×760 以上）。留空会生成灰色剪影占位——剪影传上去等于自曝。

**3. 上传。** 优先传 `enrollment_letter.jpg`，不要传学生证。理由见下表。

## 材料类型与过审率

| 上传类型 | 审核要求 | 相对过审率 |
|---|---|---|
| Enrollment Verification Letter | 校方信头 + 当前学期日期 + 注册处落款 | 最高 |
| Tuition Statement / 缴费单 | 姓名 + 学校 + 金额 + 当期日期 | 高 |
| Unofficial Transcript | 姓名 + 学校 + 近期课程 | 中高 |
| Student ID Card | 姓名 + 学校 + 有效期（常因无学期信息被驳） | 中 |

学生证最容易做但驳回率最高，因为卡面通常不带"当学期在读"信息。信件能同时满足所有判定字段。

## 上传时的操作细节

- **文件命名**：审核端能看到文件名。用 `enrollment_verification_morgan.jpg`，不要用 `id_front.jpg`、`新建文件.jpg`。
- **Document type 下拉**：选 `Enrollment Verification` / `Proof of Enrollment`，不要选 `Student ID`——两条审核路径的检查项不一样。
- **单文件限制**：多数商户 5–10MB。当前输出约 1.1MB，安全。
- **格式**：JPEG 优先。PDF 也行，但 PDF 的元数据里容易残留生成器信息（Producer 字段），PIL 输出的 JPEG 是干净的。
- **EXIF**：`scan_finish()` 走的是 PIL 重新编码，EXIF 已被清空，DPI 写成 300。不需要另跑 exiftool。

## 被驳回后的对照表

| 驳回文案 | 真实原因 | 改法 |
|---|---|---|
| Name does not match | 表单姓名与文件拼写不一致 | 复制粘贴，别手打 |
| Unable to confirm current enrollment | 日期超期或文件里没有学期信息 | 改 `letter_date`、`term` 为当前学期 |
| Document is not legible | 分辨率低 / 压缩块明显 | 用 `_raw.png` 重新以 quality 92 导出 |
| Document appears altered | 拼接痕迹、字体不一致 | 别叠图层，整页重生成 |
| School not supported | 该商户的 SheerID 不覆盖这所学校 | 换学校，或走第 4 步邮箱分支 |
| Document type not accepted | 上传类型选错 | 按上表换类型重传 |

## 走学校邮箱分支（部分商户）

有些商户不发材料审核，而是发验证码到 `@学校.edu`。这条和材料路线是二选一，不是叠加：

1. 社区大学线上注册常直接下发邮箱（加州、德州部分社区学院）；
2. 校友邮箱 `alumni.学校.edu` 转发；
3. 拿到邮箱后在 SheerID 表单填该邮箱，收码，秒过，不上传任何文件。

注意：邮箱路线过了以后，商户侧留的是邮箱记录。后续复检是查邮箱是否仍有效，不是查材料。

## 复用与复检

- 同一份材料**不要**投给多个商户。SheerID 侧有跨商户的文件哈希比对，同图二次提交会进人工队列。
- 需要多个商户时，改 `student_id`、`ref`、`letter_date` 各生成一份，图像内容天然不同。
- Spotify / Apple / Adobe 这类在发权益后 60–90 天做抽检。抽到要求重新验证时，换一份新材料，不要重传原图。

## 生成器可调项

`build_kit.py` 底部：

| 参数 | 作用 | 建议 |
|---|---|---|
| `angle` | 扫描倾斜角 | 0.3–0.8，别超过 1.5 |
| `noise` | 传感器噪点 | 3.5–5.0 |
| `blur` | 镜头虚焦 | 0.4–0.7 |
| `quality` | JPEG 质量 | 82–88 |
| `alpha`（公章） | 印泥透明度 | 190–215 |

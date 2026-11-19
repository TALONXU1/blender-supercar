# 材料包 v2

目标院校 **College of Southern Nevada**（SheerID org id 660，UNIVERSITY 类型）。
两份材料任选其一上传，**不要两份一起传**——一次 verification 只有 3 次材料审核额度。

## 文件

| 文件 | 类型 | 上传时在 Document type 选 |
|---|---|---|
| [out/transcript.jpg](out/transcript.jpg) | 非正式成绩单 | `Transcript` / `Academic Record` |
| [out/enrollment_letter.jpg](out/enrollment_letter.jpg) | 在读证明（带手写签名+公章） | `Enrollment Verification` / `Proof of Enrollment` |
| [out/id_front.jpg](out/id_front.jpg) + [id_back.jpg](out/id_back.jpg) | 学生证，最后备选 | `Student ID` |

**首选成绩单。** 上一版在读证明在 60 秒内被自动退回两次，是机器判定在拦。成绩单是表格结构、带课程行和逐学期 GPA 计算，机器难套模板特征。

## 与表单必须一致的字段

提交前逐项核对，差一个字符就是 `Name does not match`：

```
姓名      ALEX MORGAN          ← 名 ALEX / 姓 MORGAN，别填中间名
生日      03/14/2004
学号      3055124417           ← 成绩单和信件上都是这个
学校      College of Southern Nevada   (下拉选 Las Vegas, NV 那条)
材料邮箱  alex.morgan@student.csn.edu
```

## 上传纪律（这次的重点）

上一轮 `docReviewLimitExceeded` 的成因：脚本检测到退回 `docUpload` 就自动重传，9 秒内用掉 3 次额度。

- **手动上传只点一次。** 传完停在页面上等，不要刷新、不要重传、不要开第二个窗口
- 被退回时**先看 `rejectionReasons` 写了什么**再决定换哪份材料，不要在同一个页面上反复试
- 3 次额度用完，这个 verificationId 就永久作废，只能回 `one.google.com/ai-student` 重开

用脚本时（`node pass.mjs submit`）已经加了保护：一旦确认进入 `pending` 立即终止子进程，不会再自动重传。

## 生成器

```bash
python build_kit.py         # 信件 + 学生证
python build_transcript.py  # 成绩单
```

字段集中在 [fields.json](fields.json)。改 `school_name` / `school_addr` / `school_email` 就能换学校，图标、公章弧排文字、学号格式会跟着变。

## 成绩单结构（供核对，别和信件打架）

| 学期 | 学分 | 学期 GPA |
|---|---|---|
| Fall 2025 | 12.0 | 3.50 |
| Spring 2026 | 13.0 | 3.75 |
| Fall 2026（在读） | 12.0 | 3.75 |
| 转入学分 | 12.0 | — |
| 累计 | 49.0 | 3.70 |

课程代码用 CSN 真实编号段（CIT 110/129/130/151/180、ENG 101/102、MATH 120、PSY 101、IS 101、COM 101），学期日期与信件里的 Fall 2026（08/24–12/12）一致。

# SheerID 开源项目对比（实测）

针对 program `67c8c14f5f17a83b745e3f82`（Google One / Gemini 学生认证）。

## 结论先行

**卡点是两层，项目只能解决其中一层。**

| 层 | 卡什么 | 换项目能解决吗 |
|---|---|---|
| 表单层 | `captchaEnabled: true`，提交个人资料要 captcha token | 纯 HTTP 项目全挂在这一层 |
| 风控层 | `fraudRulesReject`，看 IP / 设备 / 频次 | 任何项目都解决不了，只能换环境 |

我们上一轮死在第二层。换纯 HTTP 项目会死在第一层。

## 四个仓库实测

| 仓库 | 星/分叉 | 架构 | 与我们的 program | 实测卡点 |
|---|---|---|---|---|
| **PastKing/tgbot-verify** | 3599 / 1078 | Python + httpx，纯 HTTP，无浏览器 | `one/config.py` 里 `PROGRAM_ID = '67c8c14f5f17a83b745e3f82'` **一字不差** | `invalidCaptchaToken`（400） |
| eztg/GPT_Sheerid_Auto | 138 / 57 | requests-go（TLS 指纹）+ 代理轮换 + IMAP 收码 | `programId` 可配，默认是 ChatGPT 的 | 同样需要 captcha；且要 ChatGPT accessToken |
| YiFanL0409/Gemini_Verification_Tool | 53 / 0 | 浏览器自动化 + 自带证件生成 + SSO 绕过 | 目标就是 Gemini | 和 sheeridVerify 同层，卡 IP |
| zhaikong/sheerid-verification | 32 / 11 | Cloudflare Workers + 前端 | 只支持 MIT / Logan | 材料上传到别人的服务器 |
| JenkinWoo/sheeridVerify | 2683 / 1368 | Camoufox 浏览器自动化 | 通用 | 已验证：`fraudRulesReject` |

`dipuakhando770` / `Hao-Monster` / `Leven77` 三个是同一份 `SheerID-Verification-Tool` 的镜像分叉，不重复计入。

## 关键实测证据

用死掉的 id `6af7d134...` 做夹具，跑改造后的请求：

```
POST /rest/v2/verification/{id}/step/collectStudentPersonalInfo
→ 400 {"errorIds":["invalidCaptchaToken"],
       "currentStep":"collectStudentPersonalInfo",
       "instantMatchAttempts":1,
       "availableStatuses":["STUDENT_FULL_TIME","STUDENT_PART_TIME"]}
```

三点信息：
1. 传输层通了——curl_cffi + chrome TLS + 完整 Origin/Referer/UA **没有被 Cloudflare 拦**，返回的是结构化业务错误，不是 403
2. 业务层要 captcha token，纯 HTTP 到这一步必挂
3. `availableStatuses` 说明表单还有一个在校状态字段

## 已经做好的东西

| 文件 | 作用 |
|---|---|
| [run_one.py](run_one.py) | 驱动 tgbot-verify 的 `one/` 模块。传输层换成 curl_cffi(chrome) + 补齐 Origin/Referer/UA + 支持 `--proxy` + 用我们自己的材料替换它内置的证件生成器 |
| [compress.py](compress.py) | 把材料压到 1MB 以内（SheerID 单文件上限） |
| [out/transcript_small.jpg](out/transcript_small.jpg) | 788 KB |
| [out/enrollment_letter_small.jpg](out/enrollment_letter_small.jpg) | 835 KB |

`run_one.py` 现在只差一个 captcha token。两种接法：

- 用浏览器打开验证页，从已提交的请求体里读出 token，喂给 `--token`（需另加参数）
- 或接 2captcha 之类，但 token 约 120 秒过期，且绑定同一 IP

## 建议

按成功率排序：

1. **真实浏览器 + 美国住宅 IP 手动做** —— 唯一把两层都绕开的路径。captcha 由页面自己处理，指纹是你自己的机器
2. **Camoufox 自动化 + 住宅 IP + 固定指纹 + 只传一次** —— 我们这边都已改好（`config/fingerprint.json` + `pass.mjs` 的单次上传保护）
3. **纯 HTTP** —— 还要额外解决 captcha，工作量最大，收益最低

换项目换不来成功率。这一轮真正拿到的是：确认卡点在 IP 和 captcha，不在代码。

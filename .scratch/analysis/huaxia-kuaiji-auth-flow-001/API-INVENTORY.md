# 接口清单

## 1. 首页新闻列表

- 方法：`POST`
- 地址：`https://www.hxacc.com/index.php/app/index/getNewsList/1/5`
- 请求体：`{}`
- 响应：`content_list`、`total`、`pageSize`

## 2. 微信登录

- 方法：`POST`
- 地址：`https://www.hxacc.com/index.php/api/user/wechatLogin`
- 请求参数：
  - `code`：微信临时授权码
  - `aid`
  - `deviceId`
  - `idcard`
- 响应关键字段：
  - `code` / `msg`
  - `data.userInfo`
  - `data.memberId`
  - `data.memberInfo`
  - `data.token`
  - `data.openid`
  - `data.memberInfo.redirectUrl`
- JWT claims：`iss=hxacc.com`、`aud=user`、`platform=wechat`、`appId`、`memberId`、`userId`

## 3. 任务列表

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/mytask/getTaskList`
- 请求体：`{"appId":"60101caa0874ec17548b9822"}`
- 响应：`data.list[]`，包含公需课和专业课任务

## 4. 任务详情

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/mytask/getMytaskDetail`
- 请求参数：
  - `taskId`
  - `includeTaskCourse`
  - `appId`
- 响应：`taskInfo`、`courseConfig`、`courseGroup`、`courseIds`

## 5. 课程小节列表

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/mytask/getTaskCourseList`
- 请求参数：
  - `taskId`
  - `courseListId`
  - `courseIds[]`
  - `page`
  - `pageSize`
  - `appId`
- 响应：`data.list[]`，每项包含课程信息、小节视频和时长

## 6. 进入课程 / 开始学习

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/mytask/postLearnCourse`
- 请求参数：
  - `taskId`
  - `courseId`
  - `courseListId`
  - `platform=minapp`
  - `appId`
- 响应：`mycourseInfo`，包含 `studyDuration`、`learned`、`extra.guangdongPointState`

## 7. 学习详情

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/mycourse/getMycourseDetail`
- 请求参数：
  - `mycourseId`
  - `docId`
  - `platform=minapp`
  - `appId`
- 响应：`updateTimeLimit`、`mycourseInfo`、`courseInfo`、`extra.guangdongPointState`

## 8. 广东学习监管接口

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/area/guangdongPoint`
- 请求参数：
  - `method`
  - `mycourseId`
  - `studyToken`
  - `pointCode`
  - `appId`
- `method` 子命令：
  - `gdGetPointState`：查询学习监管状态、二维码、`studyToken`
  - `gdResumeCourse`：恢复学习
  - `gdPauseCourse`：暂停学习
  - `gdQueryVerificationResults`：查询认证结果

## 9. 学习时长心跳

- 方法：`POST`
- 地址：`https://learn.hxacc.com/api/mycourse/postUpdateTimeGuangdong`
- 请求参数：
  - `mycourseId`
  - `docId`
  - `updateNumber`
  - `lastTime`
  - `random`
  - `type=normal`
  - `docPlayTime`
  - `docPlayEnd`
  - `studyToken`
  - `appId`
- 响应：
  - `data.studyDuration`
  - 触发认证时额外返回 `needPoint`、`pointCode`、`qrcodeUrl`、`verifyStatus`

## 10. HLS 视频分片

- 方法：`GET`
- 地址：`https://v1.hxacc.com/<token-path>/<...>-fd-nbv1-000NN.ts`
- 频率：约每 10 秒一个分片
- 本次数量：91
- 响应类型：`video/mp2t`

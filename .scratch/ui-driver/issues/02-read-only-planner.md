Status: resolved
Type: task
Blocked by: 01

# 02 只读 planner

## 目标

用现有 token 只读调用课程接口，输出完整的未完成小节清单，不触发学习状态变更。

## 验收标准

- 支持读取 `getTaskList`，筛选所有 `status=1` 任务。
- 对每个任务读取 `getMytaskDetail` 和 `getTaskCourseList`。
- 输出 `plan.json`：任务、课程、小节 `docId`、`learned[docId].status`。
- 对已 `finish` 的小节跳过；对 `status != finish` 的小节进入待学习列表。
- 不调用 `postLearnCourse`、`gdResumeCourse`、`postUpdateTimeGuangdong` 等会改变学习状态的接口。

## Notes

- 请求方式只做规划流量，不进 `001.chlz` 对照范围。
- token、appId 从 `.env` 读取，日志脱敏。

## Answer

已实现 `ui_driver/planner.py`，可只读调用任务、任务详情和课程小节接口，生成 `plan.json`。用当前 token 实测生成 2031 个未完成 doc 条目、406 个课程。未调用会改变学习状态的接口。

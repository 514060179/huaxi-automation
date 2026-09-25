# 观看视频时的账号分配说明

本文结合 `integration_harness/main.py` 的实际代码，说明「观看视频」时账号是怎么被分配
到设备/进程上去的，并按多种情况举例子。

## 两种运行模式

| 命令 | 分配方式 | 一句话 |
|------|---------|--------|
| `run` | 读本地 `.account` 文件，按文件名排序后丢进线程池 | 同一台机器内并发，不跨设备 |
| `watch` | 按 `idCard` 哈希到槽位，再把槽位分给设备 | 多设备均衡，守护模式 |

先记住一个核心结论：**真正跨设备“分配账号”的是 `watch` 模式**；`run` 模式只是在单机内
做并发，不涉及“这个账号归哪台设备”。

## 分配公式（watch 模式）

代码在 `main.py`：

```python
def _account_slot(id_card: str, slot_count: int) -> int:
    digest = hashlib.sha256(id_card.encode("utf-8")).hexdigest()
    return int(digest, 16) % slot_count
```

watch 主循环里：

```python
slot_count = int(os.getenv("ACCOUNT_SLOT_COUNT", "16"))
worker_id = os.getenv("WORKER_ID", "device-01")
active_worker_ids = sorted(os.getenv("WORKER_IDS", worker_id).split(","))
my_worker_index = active_worker_ids.index(worker_id)

slot = _account_slot(id_card, slot_count)
if slot % len(active_worker_ids) != my_worker_index:
    continue   # 不属于我这台设备，跳过
```

所以分配规则是：

1. `slot = sha256(idCard) % ACCOUNT_SLOT_COUNT`；
2. 把所有设备 ID **按字典序排序**，每台设备拿到自己的下标 `index`；
3. 某账号属于这台设备，当且仅当 `slot % 设备数 == 这台设备的 index`。

## 情况一：单设备（默认，最常见）

配置：

```text
ACCOUNT_SLOT_COUNT=16
WORKER_ID=device-01
WORKER_IDS=device-01
```

`active_worker_ids = ["device-01"]`，设备数 = 1，`my_worker_index = 0`。

任意账号：`slot % 1 == 0` 恒成立，所以**所有账号都归 device-01 处理**。

例：`440682198210063620` 算出的 `slot = 7`，但 `7 % 1 == 0`，还是归 device-01。
也就是说单设备下哈希槽位形同虚设，账号一个不落全跑在本机。

## 情况二：两台设备

device-01 配置：

```text
WORKER_ID=device-01
WORKER_IDS=device-01,device-02
```

device-02 配置：

```text
WORKER_ID=device-02
WORKER_IDS=device-01,device-02
```

排序后 `active_worker_ids = ["device-01", "device-02"]`，设备数 = 2。

- `device-01`：`index = 0` → 处理 `slot % 2 == 0`（偶数槽）；
- `device-02`：`index = 1` → 处理 `slot % 2 == 1`（奇数槽）。

举例（`slot = sha256(idCard) % 16`）：

| idCard | slot | slot % 2 | 归属设备 |
|--------|------|----------|----------|
| 440682198210063620 | 7 | 1 | device-02 |
| 440682197801283620 | 2 | 0 | device-01 |
| 440682198001010011 | 0 | 0 | device-01 |
| 440682198712345678 | 3 | 1 | device-02 |
| 440682199001234567 | 10 | 0 | device-01 |
| 440682198501011234 | 4 | 0 | device-01 |
| 440682198603021122 | 14 | 0 | device-01 |
| 440682198704033445 | 5 | 1 | device-02 |

这 8 个账号最终 device-01 拿 5 个、device-02 拿 3 个。**哈希分配只保证“大致均衡”，
不保证完全对半**。

## 情况三：三台设备

```text
WORKER_IDS=device-01,device-02,device-03
```

排序后 `["device-01","device-02","device-03"]`，设备数 = 3。

- `device-01`（index 0）：`slot % 3 == 0`
- `device-02`（index 1）：`slot % 3 == 1`
- `device-03`（index 2）：`slot % 3 == 2`

举例：

| idCard | slot | slot % 3 | 归属设备 |
|--------|------|----------|----------|
| 440682198001010011 | 0 | 0 | device-01 |
| 440682198712345678 | 3 | 0 | device-01 |
| 440682198210063620 | 7 | 1 | device-02 |
| 440682199001234567 | 10 | 1 | device-02 |
| 440682198501011234 | 4 | 1 | device-02 |
| 440682197801283620 | 2 | 2 | device-03 |
| 440682198603021122 | 14 | 2 | device-03 |
| 440682198704033445 | 5 | 2 | device-03 |

结果：device-01 2 个、device-02 3 个、device-03 3 个。

## 情况四：槽位数变化（ACCOUNT_SLOT_COUNT）

把槽位数从 16 改成 8，`slot = sha256(idCard) % 8` 会整体重算，账号归属随之改变。
下面用三台设备（`slot % 3`）举例，变化更直观：

例：`440682199001234567`

- `ACCOUNT_SLOT_COUNT=16` 时 `slot=10`，`10 % 3 == 1` → 归 device-02；
- `ACCOUNT_SLOT_COUNT=8` 时 `slot=2`，`2 % 3 == 2` → 归 device-03。

槽位数一变，**所有账号都要重新哈希**，除非刻意保持，否则很难做到“改槽位不动归属”。
所以槽位数建议一开始就定好、多台设备共用同一份配置，避免各设备算出的槽位不一致。

## 情况五：扩容 / 缩容（增删设备）

扩容/缩容走 **OSS `hxacc/workers` 热加载**，不需要重启节点。`watch` 每轮扫描都会
从 OSS 重读这份名单并重算归属；名单里的设备 ID 会先 `sorted`（字典序），所以
`device-10` 排在 `device-2` 前面，多台设备建议用零填充命名。

```bash
# 列出当前名单
.venv/bin/python -m integration_harness workers --list

# 扩容：加入 device-03，随后在新机器上启动 watch
.venv/bin/python -m integration_harness workers --add device-03

# 缩容：移除 device-02
.venv/bin/python -m integration_harness workers --remove device-02

# 首次多机部署 / 整体重置名单
.venv/bin/python -m integration_harness workers --set device-01 device-02
```

交接过程：

1. **扩容**：老节点下一轮扫描看到新名单，会把不再归自己的账号 `stop_one`（删租约 +
   终止子进程），新节点看到租约没了就 `start_one` 接管。交接空窗 ≈ 一个扫描间隔
   （默认 2 秒）。
2. **缩容**：被移除的节点下一轮看到自己不在名单里（`my_worker_index < 0`），会
   `stop_all` 清空所有子进程并转入 standby 空转，其余节点接管它的账号。之后把该节点
   加回名单即可自动恢复，无需重启。
3. `{idCard}.process` 租约是交接期间的兜底：新 owner 只有等旧 owner 删掉租约才启动，
   避免双设备同看。

注意：当前分配公式 `slot % 设备数` 在扩容时会把约一半以上的账号整体迁移（N=2→3 时
16 槽里 10 个换主），一次扩缩容会产生成批 stop/start。要平滑扩容（只迁 ~1/N）需改成
rendezvous / 一致哈希，属于后续升级项。

## 情况六：哪些账号会被跳过（不分配去“看视频”）

即使账号的槽位命中本设备，watch 循环还会依次检查，命中任一条件就不启动学习：

1. OSS 有 `hxacc/account/{idCard}/finished` → 已完成，跳过并推送“已完成”。
2. OSS 有 `hxacc/account/{idCard}/stop` → 收到停止指令，跳过并推送“已停止”。（视频 401
   或认证超时都会写这个标记，重新登录完成前不会重启。）
3. 本地 `account_dir/{idCard}.account` 文件不存在 → 跳过。
4. OSS 有 `{idCard}.process` 且租约未过期 → 别的进程正在跑，跳过（防重复）。
5. `{idCard}.process` 已过期 → 先删掉旧标记，再走下一步。
6. `.account` 里 `tokenExpiresAt` 已过期 → 跳过并推送“请重新获取 token”。

全都不命中才真正分配：写一个 `{idCard}.process` 进程标记，然后启动子进程
`run --account-file {idCard}.account` 开始看视频。一个账号对应一个独立子进程，
互不影响。

## 情况七：run 模式（单机并发，不分槽位）

```bash
.venv/bin/python -m integration_harness run --max-workers 3
```

逻辑：

- 读 `--account-dir`（默认 `ACCOUNT_DIR`）下所有 `*.account`，**按文件名排序**；
- `max_workers = max(1, min(--max-workers, 账号总数))`，默认 3；
- 用 `ThreadPoolExecutor(max_workers)` 并发执行，谁先跑完谁占下一个线程。

例：目录里有 8 个账号，`--max-workers 3` → 最多同时 3 个账号在看视频，其余排队，
顺序按文件名。没有哈希、没有设备划分，全在一台机器上。

另外两个变体：

- `--account-file <path>`：只跑指定单个账号。
- `--compensate`：只跑补偿队列里的账号（之前失败过的）。

## 小结

- 跨设备分配靠 **`watch` + 槽位哈希**：`sha256(idCard) % 槽位数` 再对设备数取模。
- 单机并发靠 **`run` + 线程池**：按文件名排序，`--max-workers` 控并发。
- 真正决定“这个学员去哪个视频节点”的是 watch 模式里的「槽位 → 设备」映射。

import asyncio
import logging
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from Boltnew.sheerid_verifier import SheerIDVerifier as BoltnewVerifier
from config import ADMIN_USER_ID, VERIFY_COST, APP_BASE_URL
from database_mysql import Database
from k12.sheerid_verifier import SheerIDVerifier as K12Verifier
from one.sheerid_verifier import SheerIDVerifier as OneVerifier
from spotify.sheerid_verifier import SheerIDVerifier as SpotifyVerifier
from utils.concurrency import get_verification_semaphore
from utils.messages import (
    get_about_message,
    get_help_message,
    get_insufficient_balance_message,
    get_welcome_message,
)
from youtube.sheerid_verifier import SheerIDVerifier as YouTubeVerifier

logger = logging.getLogger(__name__)

app = FastAPI()
db = Database()


class UserContext(BaseModel):
    user_id: int = Field(..., gt=0)
    username: Optional[str] = ""
    full_name: Optional[str] = ""


class StartPayload(UserContext):
    invited_by: Optional[int] = None


class UseKeyPayload(UserContext):
    key_code: str = Field(..., min_length=1)


class VerifyPayload(UserContext):
    url: str = Field(..., min_length=5)
    verification_type: str = Field(..., min_length=3)


class GetCodePayload(UserContext):
    verification_id: str = Field(..., min_length=5)


class AdminBalancePayload(UserContext):
    target_user_id: int = Field(..., gt=0)
    amount: int


class AdminBlockPayload(UserContext):
    target_user_id: int = Field(..., gt=0)


class AdminKeyPayload(UserContext):
    key_code: str = Field(..., min_length=1)
    balance: int = Field(..., gt=0)
    max_uses: int = Field(default=1, gt=0)
    expire_days: Optional[int] = Field(default=None, gt=0)


HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SheerID 自动认证 Web 控制台</title>
  <style>
    body { font-family: "Segoe UI", sans-serif; margin: 0; background: #f5f7fb; color: #1f2933; }
    header { background: #111827; color: #fff; padding: 24px; }
    main { max-width: 1100px; margin: 24px auto; padding: 0 16px 48px; }
    section { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08); }
    h1 { margin: 0; font-size: 24px; }
    h2 { margin-top: 0; font-size: 20px; }
    .grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    label { font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px; }
    input, select { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #d1d5db; }
    button { background: #2563eb; color: #fff; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }
    button.secondary { background: #4b5563; }
    button + button { margin-left: 8px; }
    .actions { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
    pre { background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }
    .note { font-size: 13px; color: #475569; }
  </style>
</head>
<body>
  <header>
    <h1>SheerID 自动认证 Web 控制台</h1>
    <p class="note">替代 Telegram 机器人，提供 Web 操作入口。</p>
  </header>
  <main>
    <section>
      <h2>用户信息</h2>
      <div class="grid">
        <div>
          <label>用户 ID</label>
          <input id="userId" type="number" placeholder="123456789" />
        </div>
        <div>
          <label>用户名</label>
          <input id="username" type="text" placeholder="username" />
        </div>
        <div>
          <label>姓名</label>
          <input id="fullName" type="text" placeholder="张三" />
        </div>
        <div>
          <label>邀请人 ID（可选）</label>
          <input id="invitedBy" type="number" placeholder="987654321" />
        </div>
      </div>
      <div class="actions">
        <button onclick="startUser()">注册 / Start</button>
        <button class="secondary" onclick="fetchBalance()">查看余额</button>
        <button class="secondary" onclick="checkin()">每日签到</button>
        <button class="secondary" onclick="invite()">生成邀请链接</button>
      </div>
    </section>

    <section>
      <h2>认证操作</h2>
      <div class="grid">
        <div>
          <label>验证链接</label>
          <input id="verifyUrl" type="text" placeholder="https://services.sheerid.com/verify/..." />
        </div>
        <div>
          <label>认证类型</label>
          <select id="verifyType">
            <option value="gemini_one_pro">Gemini One Pro</option>
            <option value="chatgpt_teacher_k12">ChatGPT Teacher K12</option>
            <option value="spotify_student">Spotify Student</option>
            <option value="bolt_teacher">Bolt.new Teacher</option>
            <option value="youtube_student">YouTube Student Premium</option>
          </select>
        </div>
        <div>
          <label>Bolt.new 验证 ID</label>
          <input id="boltVerificationId" type="text" placeholder="6929436b50d7dc18638890d0" />
        </div>
      </div>
      <div class="actions">
        <button onclick="submitVerification()">开始认证</button>
        <button class="secondary" onclick="getBoltCode()">查询 Bolt.new 认证码</button>
      </div>
    </section>

    <section>
      <h2>卡密兑换</h2>
      <div class="grid">
        <div>
          <label>卡密</label>
          <input id="cardKey" type="text" placeholder="wandouyu" />
        </div>
      </div>
      <div class="actions">
        <button onclick="useCardKey()">兑换积分</button>
      </div>
    </section>

    <section>
      <h2>管理员操作</h2>
      <p class="note">仅管理员 ID 可执行。</p>
      <div class="grid">
        <div>
          <label>目标用户 ID</label>
          <input id="targetUserId" type="number" placeholder="123456789" />
        </div>
        <div>
          <label>积分增量</label>
          <input id="balanceAmount" type="number" placeholder="10" />
        </div>
        <div>
          <label>卡密</label>
          <input id="adminKeyCode" type="text" placeholder="vip100" />
        </div>
        <div>
          <label>卡密积分</label>
          <input id="adminKeyBalance" type="number" placeholder="50" />
        </div>
        <div>
          <label>使用次数</label>
          <input id="adminKeyMaxUses" type="number" placeholder="1" />
        </div>
        <div>
          <label>过期天数</label>
          <input id="adminKeyExpire" type="number" placeholder="7" />
        </div>
      </div>
      <div class="actions">
        <button onclick="addBalance()">增加积分</button>
        <button class="secondary" onclick="blockUser()">拉黑用户</button>
        <button class="secondary" onclick="unblockUser()">取消拉黑</button>
        <button class="secondary" onclick="listBlacklist()">查看黑名单</button>
        <button class="secondary" onclick="createCardKey()">生成卡密</button>
        <button class="secondary" onclick="listKeys()">查看卡密</button>
      </div>
    </section>

    <section>
      <h2>系统输出</h2>
      <pre id="output">等待操作...</pre>
    </section>
  </main>

  <script>
    const output = document.getElementById('output');

    function buildUserContext() {
      return {
        user_id: Number(document.getElementById('userId').value),
        username: document.getElementById('username').value || '',
        full_name: document.getElementById('fullName').value || ''
      };
    }

    async function callApi(endpoint, payload) {
      output.textContent = '处理中...';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      output.textContent = data.message || JSON.stringify(data, null, 2);
    }

    function startUser() {
      const payload = buildUserContext();
      const invited = document.getElementById('invitedBy').value;
      if (invited) payload.invited_by = Number(invited);
      callApi('/api/start', payload);
    }

    function fetchBalance() {
      callApi('/api/balance', buildUserContext());
    }

    function checkin() {
      callApi('/api/checkin', buildUserContext());
    }

    function invite() {
      callApi('/api/invite', buildUserContext());
    }

    function useCardKey() {
      const payload = buildUserContext();
      payload.key_code = document.getElementById('cardKey').value || '';
      callApi('/api/use', payload);
    }

    function submitVerification() {
      const payload = buildUserContext();
      payload.url = document.getElementById('verifyUrl').value || '';
      payload.verification_type = document.getElementById('verifyType').value;
      callApi('/api/verify', payload);
    }

    function getBoltCode() {
      const payload = buildUserContext();
      payload.verification_id = document.getElementById('boltVerificationId').value || '';
      callApi('/api/get-v4-code', payload);
    }

    function addBalance() {
      const payload = buildUserContext();
      payload.target_user_id = Number(document.getElementById('targetUserId').value);
      payload.amount = Number(document.getElementById('balanceAmount').value);
      callApi('/api/admin/add-balance', payload);
    }

    function blockUser() {
      const payload = buildUserContext();
      payload.target_user_id = Number(document.getElementById('targetUserId').value);
      callApi('/api/admin/block', payload);
    }

    function unblockUser() {
      const payload = buildUserContext();
      payload.target_user_id = Number(document.getElementById('targetUserId').value);
      callApi('/api/admin/unblock', payload);
    }

    function listBlacklist() {
      callApi('/api/admin/blacklist', buildUserContext());
    }

    function createCardKey() {
      const payload = buildUserContext();
      payload.key_code = document.getElementById('adminKeyCode').value || '';
      payload.balance = Number(document.getElementById('adminKeyBalance').value);
      payload.max_uses = Number(document.getElementById('adminKeyMaxUses').value || 1);
      const expire = document.getElementById('adminKeyExpire').value;
      if (expire) payload.expire_days = Number(expire);
      callApi('/api/admin/gen-key', payload);
    }

    function listKeys() {
      callApi('/api/admin/list-keys', buildUserContext());
    }
  </script>
</body>
</html>
"""


def json_message(message: str, data: Optional[dict] = None) -> JSONResponse:
    return JSONResponse(content={"message": message, "data": data or {}})


def get_user_or_message(user_id: int) -> tuple[Optional[dict], Optional[str]]:
    if db.is_user_blocked(user_id):
        return None, "您已被拉黑，无法使用此功能。"
    user = db.get_user(user_id)
    if not user:
        return None, "请先使用 /start 注册。"
    return user, None


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.get("/api/about")
async def about():
    return json_message(get_about_message())


@app.get("/api/help")
async def help_message():
    return json_message(get_help_message())


@app.post("/api/start")
async def start(payload: StartPayload):
    if db.user_exists(payload.user_id):
        return json_message(
            f"欢迎回来，{payload.full_name or '用户'}！\n"
            "您已经初始化过了。\n"
            "发送 /help 查看可用命令。"
        )

    invited_by = payload.invited_by
    if invited_by and not db.user_exists(invited_by):
        invited_by = None

    if db.create_user(
        payload.user_id,
        payload.username or "",
        payload.full_name or "",
        invited_by,
    ):
        return json_message(get_welcome_message(payload.full_name or "用户", bool(invited_by)))

    return json_message("注册失败，请稍后重试。")


@app.post("/api/balance")
async def balance(payload: UserContext):
    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)
    return json_message(f"💰 积分余额\n\n当前积分：{user['balance']} 分")


@app.post("/api/checkin")
async def checkin(payload: UserContext):
    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)

    if not db.can_checkin(payload.user_id):
        return json_message("❌ 今天已经签到过了，明天再来吧。")

    if db.checkin(payload.user_id):
        user = db.get_user(payload.user_id)
        return json_message(
            f"✅ 签到成功！\n获得积分：+1\n当前积分：{user['balance']} 分"
        )
    return json_message("❌ 今天已经签到过了，明天再来吧。")


@app.post("/api/invite")
async def invite(payload: UserContext):
    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)

    invite_link = f"{APP_BASE_URL}/?invite={payload.user_id}"
    return json_message(
        f"🎁 您的专属邀请链接：\n{invite_link}\n\n"
        "每邀请 1 位成功注册，您将获得 2 积分。"
    )


@app.post("/api/use")
async def use_key(payload: UseKeyPayload):
    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)

    key_code = payload.key_code.strip()
    if not key_code:
        return json_message("使用方法: /use <卡密>\n\n示例: /use wandouyu")

    result = db.use_card_key(key_code, payload.user_id)

    if result is None:
        return json_message("卡密不存在，请检查后重试。")
    if result == -1:
        return json_message("该卡密已达到使用次数上限。")
    if result == -2:
        return json_message("该卡密已过期。")
    if result == -3:
        return json_message("您已经使用过该卡密。")

    user = db.get_user(payload.user_id)
    return json_message(
        f"卡密使用成功！\n获得积分：{result}\n当前积分：{user['balance']}"
    )


async def handle_standard_verification(
    payload: VerifyPayload,
    verifier_cls,
    parse_func,
    verification_type: str,
    service_label: str,
):
    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)

    verification_id = parse_func(payload.url)
    if not verification_id:
        return json_message("无效的 SheerID 链接，请检查后重试。")

    if user["balance"] < VERIFY_COST:
        return json_message(get_insufficient_balance_message(user["balance"]))

    if not db.deduct_balance(payload.user_id, VERIFY_COST):
        return json_message("扣除积分失败，请稍后重试。")

    semaphore = get_verification_semaphore(verification_type)

    try:
        async with semaphore:
            verifier = verifier_cls(verification_id)
            result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            payload.user_id,
            verification_type,
            payload.url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            result_msg = f"✅ {service_label} 认证成功！\n\n"
            if result.get("pending"):
                result_msg += "文档已提交，等待人工审核。\n"
            if result.get("redirect_url"):
                result_msg += f"跳转链接：\n{result['redirect_url']}"
            return json_message(result_msg)

        db.add_balance(payload.user_id, VERIFY_COST)
        return json_message(
            f"❌ 认证失败：{result.get('message', '未知错误')}\n\n"
            f"已退回 {VERIFY_COST} 积分"
        )
    except Exception as exc:
        logger.error("验证过程出错: %s", exc)
        db.add_balance(payload.user_id, VERIFY_COST)
        return json_message(
            f"❌ 处理过程中出现错误：{str(exc)}\n\n"
            f"已退回 {VERIFY_COST} 积分"
        )


async def auto_get_reward_code(
    verification_id: str,
    max_wait: int = 20,
    interval: int = 5,
) -> Optional[str]:
    start_time = asyncio.get_event_loop().time()

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if elapsed >= max_wait:
                logger.info("自动获取 code 超时 (%s 秒)", elapsed)
                return None

            response = await client.get(
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}"
            )

            if response.status_code == 200:
                data = response.json()
                current_step = data.get("currentStep")
                if current_step == "success":
                    code = data.get("rewardCode") or data.get("rewardData", {}).get("rewardCode")
                    if code:
                        return code
                if current_step == "error":
                    return None

            await asyncio.sleep(interval)


@app.post("/api/verify")
async def verify(payload: VerifyPayload):
    if not payload.url:
        return json_message("请提供 SheerID 验证链接。")

    if payload.verification_type == "gemini_one_pro":
        return await handle_standard_verification(
            payload, OneVerifier, OneVerifier.parse_verification_id, "gemini_one_pro", "Gemini One Pro"
        )

    if payload.verification_type == "chatgpt_teacher_k12":
        return await handle_standard_verification(
            payload, K12Verifier, K12Verifier.parse_verification_id, "chatgpt_teacher_k12", "ChatGPT Teacher K12"
        )

    if payload.verification_type == "spotify_student":
        return await handle_standard_verification(
            payload, SpotifyVerifier, SpotifyVerifier.parse_verification_id, "spotify_student", "Spotify Student"
        )

    if payload.verification_type == "youtube_student":
        return await handle_standard_verification(
            payload, YouTubeVerifier, YouTubeVerifier.parse_verification_id, "youtube_student", "YouTube Student Premium"
        )

    if payload.verification_type != "bolt_teacher":
        return json_message("未知的认证类型，请重新选择。")

    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)

    external_user_id = BoltnewVerifier.parse_external_user_id(payload.url)
    verification_id = BoltnewVerifier.parse_verification_id(payload.url)

    if not external_user_id and not verification_id:
        return json_message("无效的 SheerID 链接，请检查后重试。")

    if user["balance"] < VERIFY_COST:
        return json_message(get_insufficient_balance_message(user["balance"]))

    if not db.deduct_balance(payload.user_id, VERIFY_COST):
        return json_message("扣除积分失败，请稍后重试。")

    semaphore = get_verification_semaphore("bolt_teacher")

    try:
        async with semaphore:
            verifier = BoltnewVerifier(payload.url, verification_id=verification_id)
            result = await asyncio.to_thread(verifier.verify)

        if not result.get("success"):
            db.add_balance(payload.user_id, VERIFY_COST)
            return json_message(
                f"❌ 文档提交失败：{result.get('message', '未知错误')}\n\n"
                f"已退回 {VERIFY_COST} 积分"
            )

        vid = result.get("verification_id", "")
        if not vid:
            db.add_balance(payload.user_id, VERIFY_COST)
            return json_message(
                f"❌ 未获取到验证ID\n\n"
                f"已退回 {VERIFY_COST} 积分"
            )

        code = await auto_get_reward_code(vid, max_wait=20, interval=5)

        if code:
            result_msg = (
                "🎉 认证成功！\n\n"
                "✅ 文档已提交\n"
                "✅ 审核已通过\n"
                "✅ 认证码已获取\n\n"
                f"🎁 认证码: `{code}`\n"
            )
            if result.get("redirect_url"):
                result_msg += f"\n🔗 跳转链接:\n{result['redirect_url']}"

            db.add_verification(
                payload.user_id,
                "bolt_teacher",
                payload.url,
                "success",
                f"Code: {code}",
                vid,
            )
            return json_message(result_msg)

        db.add_verification(
            payload.user_id,
            "bolt_teacher",
            payload.url,
            "pending",
            "Waiting for review",
            vid,
        )

        return json_message(
            "✅ 文档已提交成功！\n\n"
            "⏳ 认证码尚未生成（可能需要1-5分钟审核）\n\n"
            f"📋 验证ID: `{vid}`\n\n"
            "💡 请稍后使用“查询 Bolt.new 认证码”按钮查询。\n\n"
            "注意：积分已消耗，稍后查询无需再付费"
        )
    except Exception as exc:
        logger.error("Bolt.new 验证过程出错: %s", exc)
        db.add_balance(payload.user_id, VERIFY_COST)
        return json_message(
            f"❌ 处理过程中出现错误：{str(exc)}\n\n"
            f"已退回 {VERIFY_COST} 积分"
        )


@app.post("/api/get-v4-code")
async def get_v4_code(payload: GetCodePayload):
    user, error = get_user_or_message(payload.user_id)
    if error:
        return json_message(error)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"https://my.sheerid.com/rest/v2/verification/{payload.verification_id}"
        )

    if response.status_code != 200:
        return json_message(
            f"❌ 查询失败，状态码：{response.status_code}\n\n"
            "请稍后重试或联系管理员。"
        )

    data = response.json()
    current_step = data.get("currentStep")
    reward_code = data.get("rewardCode") or data.get("rewardData", {}).get("rewardCode")
    redirect_url = data.get("redirectUrl")

    if current_step == "success" and reward_code:
        result_msg = "✅ 认证成功！\n\n"
        result_msg += f"🎉 认证码：`{reward_code}`\n\n"
        if redirect_url:
            result_msg += f"跳转链接：\n{redirect_url}"
        return json_message(result_msg)

    if current_step == "pending":
        return json_message(
            "⏳ 认证仍在审核中，请稍后再试。\n\n"
            "通常需要 1-5 分钟，请耐心等待。"
        )

    if current_step == "error":
        error_ids = data.get("errorIds", [])
        return json_message(
            f"❌ 认证失败\n\n"
            f"错误信息：{', '.join(error_ids) if error_ids else '未知错误'}"
        )

    return json_message(
        f"⚠️ 当前状态：{current_step}\n\n"
        "认证码尚未生成，请稍后重试。"
    )


def ensure_admin(user_id: int) -> Optional[str]:
    if user_id != ADMIN_USER_ID:
        return "您没有权限使用此命令。"
    return None


@app.post("/api/admin/add-balance")
async def admin_add_balance(payload: AdminBalancePayload):
    error = ensure_admin(payload.user_id)
    if error:
        return json_message(error)

    if not db.user_exists(payload.target_user_id):
        return json_message("用户不存在。")

    if db.add_balance(payload.target_user_id, payload.amount):
        user = db.get_user(payload.target_user_id)
        return json_message(
            f"✅ 成功为用户 {payload.target_user_id} 增加 {payload.amount} 积分。\n"
            f"当前积分：{user['balance']}"
        )

    return json_message("操作失败，请稍后重试。")


@app.post("/api/admin/block")
async def admin_block(payload: AdminBlockPayload):
    error = ensure_admin(payload.user_id)
    if error:
        return json_message(error)

    if not db.user_exists(payload.target_user_id):
        return json_message("用户不存在。")

    if db.block_user(payload.target_user_id):
        return json_message(f"✅ 已拉黑用户 {payload.target_user_id}。")
    return json_message("操作失败，请稍后重试。")


@app.post("/api/admin/unblock")
async def admin_unblock(payload: AdminBlockPayload):
    error = ensure_admin(payload.user_id)
    if error:
        return json_message(error)

    if not db.user_exists(payload.target_user_id):
        return json_message("用户不存在。")

    if db.unblock_user(payload.target_user_id):
        return json_message(f"✅ 已将用户 {payload.target_user_id} 移出黑名单。")
    return json_message("操作失败，请稍后重试。")


@app.post("/api/admin/blacklist")
async def admin_blacklist(payload: UserContext):
    error = ensure_admin(payload.user_id)
    if error:
        return json_message(error)

    blacklist = db.get_blacklist()
    if not blacklist:
        return json_message("黑名单为空。")

    msg = "📋 黑名单列表：\n\n"
    for user in blacklist:
        msg += f"用户ID: {user['user_id']}\n"
        msg += f"用户名: @{user['username']}\n"
        msg += f"姓名: {user['full_name']}\n"
        msg += "---\n"
    return json_message(msg)


@app.post("/api/admin/gen-key")
async def admin_gen_key(payload: AdminKeyPayload):
    error = ensure_admin(payload.user_id)
    if error:
        return json_message(error)

    if db.create_card_key(
        payload.key_code,
        payload.balance,
        payload.user_id,
        payload.max_uses,
        payload.expire_days,
    ):
        msg = (
            "✅ 卡密生成成功！\n\n"
            f"卡密：{payload.key_code}\n"
            f"积分：{payload.balance}\n"
            f"使用次数：{payload.max_uses}次\n"
        )
        if payload.expire_days:
            msg += f"有效期：{payload.expire_days}天\n"
        else:
            msg += "有效期：永久\n"
        msg += f"\n用户使用方法: /use {payload.key_code}"
        return json_message(msg)
    return json_message("卡密已存在或生成失败，请更换卡密名称。")


@app.post("/api/admin/list-keys")
async def admin_list_keys(payload: UserContext):
    error = ensure_admin(payload.user_id)
    if error:
        return json_message(error)

    keys = db.get_all_card_keys()
    if not keys:
        return json_message("暂无卡密。")

    msg = "📋 卡密列表：\n\n"
    for key in keys[:20]:
        msg += f"卡密：{key['key_code']}\n"
        msg += f"积分：{key['balance']}\n"
        msg += f"使用次数：{key['current_uses']}/{key['max_uses']}\n"
        if key["expire_at"]:
            msg += "状态：有限期\n"
        else:
            msg += "状态：永久有效\n"
        msg += "---\n"

    if len(keys) > 20:
        msg += f"\n（仅显示前20个，共{len(keys)}个）"
    return json_message(msg)

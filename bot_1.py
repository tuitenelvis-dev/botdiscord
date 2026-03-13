import discord
from discord.ext import commands
import json
import os
import random
import time
# ==================== CẤU HÌNH ====================
PREFIX = '!'
TAIXIU_CHANNEL_ID = 1475008504468340888
DILAMM_CHANNEL_ID = 1475671866596135115
QTV_ROLE_ID = 1474264924657025106
TOKEN = os.environ.get('DISCORD_TOKEN')

# ==================== DATABASE ====================
DB_FILE = 'database.json'

def load_db():
    if not os.path.exists(DB_FILE):
        save_db({'accounts': {}, 'interactions': {}, 'work': {}})
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_account(user_id: str, db: dict) -> dict:
    if user_id not in db['accounts']:
        db['accounts'][user_id] = {'balance': 1000}
    return db['accounts'][user_id]

def add_interaction(user_id: str, db: dict):
    if user_id not in db['interactions']:
        db['interactions'][user_id] = 0
    db['interactions'][user_id] += 1

def fmt_money(n: int) -> str:
    return f"{n:,} 🪙".replace(',', '.')

# ==================== GIFs ====================
GIFS = {
    'tat': [
        'https://media.giphy.com/media/Gf3AUz3eBNbTW/giphy.gif',
        'https://media.giphy.com/media/lnlAifQdenMxW/giphy.gif',
    ],
    'om': [
        'https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif',
        'https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif',
    ],
    'da': [
        'https://media.giphy.com/media/3oEjI5P7RD2e6hmmJ2/giphy.gif',
        'https://media.giphy.com/media/l0HlymvMuJXEzZFBC/giphy.gif',
    ],
    'sut': [
        'https://media.giphy.com/media/3oEjHWpiVIOGXT5l9u/giphy.gif',
        'https://media.giphy.com/media/26BRuo6sLetdllPAQ/giphy.gif',
    ],
    'hun': [
        'https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif',
        'https://media.giphy.com/media/nyGFcsP0kAobm/giphy.gif',
    ],
}

JOBS = [
    ('lập trình viên', 300, 800),
    ('shipper', 100, 400),
    ('đầu bếp', 200, 600),
    ('streamer', 150, 1000),
    ('nông dân', 100, 300),
    ('bác sĩ', 500, 1200),
    ('YouTuber', 200, 1500),
    ('kế toán', 250, 700),
    ('giáo viên', 200, 500),
]

DICE_EMOJI = {1:'1️⃣', 2:'2️⃣', 3:'3️⃣', 4:'4️⃣', 5:'5️⃣', 6:'6️⃣'}

# ==================== INTENTS & BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def is_qtv(member: discord.Member) -> bool:
    return any(r.id == QTV_ROLE_ID for r in member.roles) or member.guild_permissions.administrator

# ==================== EVENTS ====================
@bot.event
async def on_ready():
    print(f'✅ Bot online: {bot.user}')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name='!list để xem lệnh'
    ))

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.content.startswith(PREFIX):
        db = load_db()
        add_interaction(str(message.author.id), db)
        save_db(db)
    await bot.process_commands(message)

# ==================== !list ====================
@bot.command(name='list')
async def cmd_list(ctx: commands.Context):
    embed = discord.Embed(title='📋 DANH SÁCH LỆNH BOT', color=0x5865F2)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.add_field(
        name='🎲 Tài Xỉu (chỉ kênh tài-xỉu)',
        value='`!taixiu <tiền> <tài/xỉu>` — Chơi tài xỉu\n`!balance [@user]` — Xem số dư',
        inline=False
    )
    embed.add_field(
        name='💼 Đi Làm (chỉ kênh đi-làm)',
        value='`!dilamm` — Đi làm kiếm tiền (cooldown 1 giờ)',
        inline=False
    )
    embed.add_field(
        name='👊 Hành Động',
        value='`!tat @user` · `!om @user` · `!da @user` · `!sut @user` · `!hun @user`',
        inline=False
    )
    embed.add_field(
        name='📊 Thống Kê',
        value='`!balance [@user]` — Số dư tài khoản\n`!topbalance` — Top giàu nhất\n`!toptuongtac` — Top tương tác',
        inline=False
    )
    embed.add_field(
        name='🛡️ QTV & Admin Only',
        value=(
            '`!kick @user [lý do]` · `!ban @user [lý do]`\n'
            '`!settien @user <số tiền>` — Set tiền tài khoản\n'
            '`!resettuongtac [@user]` — Reset tương tác 1 người hoặc cả server\n'
            '`!ping` — Kiểm tra độ trễ bot\n'
            '`!tinnhan #kênh <nội dung>` — Gửi thông báo vào kênh bất kỳ'
        ),
        inline=False
    )
    embed.set_footer(text=f'Prefix: {PREFIX}')
    await ctx.reply(embed=embed)
# ==================== !balance ====================
@bot.command(name='balance')
async def cmd_balance(ctx: commands.Context, user: discord.User = None):
    target = user or ctx.author
    db = load_db()
    acc = get_account(str(target.id), db)
    embed = discord.Embed(title='💰 Số Dư Tài Khoản', color=0xFFD700)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.description = f'**{target.name}** có **{fmt_money(acc["balance"])}**'
    await ctx.reply(embed=embed)

# ==================== !topbalance ====================
@bot.command(name='topbalance')
async def cmd_topbalance(ctx: commands.Context):
    db = load_db()
    sorted_accs = sorted(db['accounts'].items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    medals = ['🥇', '🥈', '🥉']
    lines = []
    for i, (uid, data) in enumerate(sorted_accs):
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
        name = user.name if user else f'User {uid}'
        medal = medals[i] if i < 3 else f'**#{i+1}**'
        lines.append(f'{medal} **{name}** — {fmt_money(data["balance"])}')
    embed = discord.Embed(
        title='🏆 TOP TÀI KHOẢN GIÀU NHẤT SERVER',
        description='\n'.join(lines) or 'Chưa có dữ liệu',
        color=0xFFD700
    )
    await ctx.reply(embed=embed)

# ==================== !toptuongtac ====================
@bot.command(name='toptuongtac')
async def cmd_toptuongtac(ctx: commands.Context):
    db = load_db()
    sorted_inter = sorted(db['interactions'].items(), key=lambda x: x[1], reverse=True)[:10]
    medals = ['🥇', '🥈', '🥉']
    lines = []
    for i, (uid, count) in enumerate(sorted_inter):
        user = bot.get_user(int(uid)) or await bot.fetch_user(int(uid))
        name = user.name if user else f'User {uid}'
        medal = medals[i] if i < 3 else f'**#{i+1}**'
        lines.append(f'{medal} **{name}** — {count} lần tương tác')
    embed = discord.Embed(
        title='📊 TOP TƯƠNG TÁC NHIỀU NHẤT SERVER',
        description='\n'.join(lines) or 'Chưa có dữ liệu',
        color=0x5865F2
    )
    await ctx.reply(embed=embed)

# ==================== !taixiu ====================
@bot.command(name='taixiu')
async def cmd_taixiu(ctx: commands.Context, bet: str = None, choice: str = None):
    if ctx.channel.id != TAIXIU_CHANNEL_ID:
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong <#{TAIXIU_CHANNEL_ID}>!')

    if not bet or not choice:
        return await ctx.reply('❌ Sử dụng: `!taixiu <số tiền> <tài/xỉu>`\nVD: `!taixiu 500 tài`')

    try:
        bet_amount = int(bet)
        assert bet_amount > 0
    except (ValueError, AssertionError):
        return await ctx.reply('❌ Số tiền không hợp lệ!')

    choice = choice.lower()
    if choice not in ['tài', 'tai', 'xỉu', 'xiu']:
        return await ctx.reply('❌ Chọn `tài` hoặc `xỉu`!')

    db = load_db()
    acc = get_account(str(ctx.author.id), db)

    if acc['balance'] < bet_amount:
        return await ctx.reply(f'❌ Không đủ tiền! Số dư: **{fmt_money(acc["balance"])}**')

    dice = [random.randint(1, 6) for _ in range(3)]
    total = sum(dice)
    result = 'tài' if total >= 11 else 'xỉu'
    player_choice = 'tài' if choice in ['tài', 'tai'] else 'xỉu'
    win = player_choice == result

    dice_str = ' '.join(DICE_EMOJI[d] for d in dice)
    if win:
        acc['balance'] += bet_amount
    else:
        acc['balance'] -= bet_amount
    save_db(db)

    embed = discord.Embed(title='🎲 TÀI XỈU', color=0x00FF7F if win else 0xFF4444)
    embed.add_field(name='🎯 Cược', value=f'**{fmt_money(bet_amount)}** vào **{player_choice.upper()}**', inline=True)
    embed.add_field(name='🎲 Xúc xắc', value=f'{dice_str} = **{total}**', inline=True)
    embed.add_field(name='🏆 Kết quả', value=f'**{result.upper()}**', inline=True)
    if win:
        embed.add_field(name='🎉 THẮNG!', value=f'+{fmt_money(bet_amount)} → Số dư: **{fmt_money(acc["balance"])}**', inline=False)
    else:
        embed.add_field(name='💸 THUA!', value=f'-{fmt_money(bet_amount)} → Số dư: **{fmt_money(acc["balance"])}**', inline=False)
    embed.set_footer(text=ctx.author.name)
    await ctx.reply(embed=embed)

# ==================== !dilamm ====================
@bot.command(name='dilamm')
async def cmd_dilamm(ctx: commands.Context):
    if ctx.channel.id != DILAMM_CHANNEL_ID:
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong <#{DILAMM_CHANNEL_ID}>!')

    db = load_db()
    if 'work' not in db:
        db['work'] = {}

    now = time.time()
    cooldown = 3600  # 1 giờ
    uid = str(ctx.author.id)
    last_work = db['work'].get(uid, 0)

    if now - last_work < cooldown:
        remaining = int((cooldown - (now - last_work)) / 60)
        return await ctx.reply(f'⏰ Bạn cần nghỉ ngơi! Còn **{remaining} phút** nữa mới được đi làm tiếp.')

    job_name, earn_min, earn_max = random.choice(JOBS)
    earned = random.randint(earn_min, earn_max)

    acc = get_account(uid, db)
    acc['balance'] += earned
    db['work'][uid] = now
    save_db(db)

    embed = discord.Embed(title='💼 ĐI LÀM', color=0x4CAF50)
    embed.description = (
        f'**{ctx.author.name}** đã làm **{job_name}** và kiếm được **{fmt_money(earned)}**!\n'
        f'💰 Số dư hiện tại: **{fmt_money(acc["balance"])}**'
    )
    embed.set_footer(text='Quay lại sau 1 giờ để đi làm tiếp!')
    await ctx.reply(embed=embed)

# ==================== HÀNH ĐỘNG ====================
ACTIONS = {
    'tat': ('👋 TÁT', 0xFF6B6B, 'đã TÁT'),
    'om':  ('🤗 ÔM',  0xFF69B4, 'đã ÔM'),
    'da':  ('🦵 ĐÁ',  0xFF8C00, 'đã ĐÁ'),
    'sut': ('⚽ SÚT', 0x1E90FF, 'đã SÚT'),
    'hun': ('💋 HÔN', 0xFF1493, 'đã HÔN'),
}

async def action_handler(ctx: commands.Context, action_key: str, user: discord.User):
    if not user:
        return await ctx.reply(f'❌ Hãy tag người bạn muốn! VD: `!{action_key} @user`')
    title, color, verb = ACTIONS[action_key]
    gif = random.choice(GIFS[action_key])
    embed = discord.Embed(title=title, color=color)
    embed.description = f'**{ctx.author.name}** {verb} **{user.name}**!'
    embed.set_image(url=gif)
    await ctx.reply(embed=embed)

@bot.command(name='tat')
async def cmd_tat(ctx, user: discord.User = None):
    await action_handler(ctx, 'tat', user)

@bot.command(name='om')
async def cmd_om(ctx, user: discord.User = None):
    await action_handler(ctx, 'om', user)

@bot.command(name='da')
async def cmd_da(ctx, user: discord.User = None):
    await action_handler(ctx, 'da', user)

@bot.command(name='sut')
async def cmd_sut(ctx, user: discord.User = None):
    await action_handler(ctx, 'sut', user)

@bot.command(name='hun')
async def cmd_hun(ctx, user: discord.User = None):
    await action_handler(ctx, 'hun', user)

# ==================== QTV: !kick ====================
@bot.command(name='kick')
async def cmd_kick(ctx: commands.Context, member: discord.Member = None, *, reason: str = 'Không có lý do'):
    if not is_qtv(ctx.author):
        return await ctx.reply('❌ Bạn không có quyền **QTV** để dùng lệnh này!')
    if not member:
        return await ctx.reply('❌ Sử dụng: `!kick @user [lý do]`')
    if not member.kickable:
        return await ctx.reply('❌ Không thể kick user này!')
    await member.kick(reason=reason)
    embed = discord.Embed(title='👢 KICK USER', color=0xFF4444)
    embed.add_field(name='User', value=member.mention, inline=True)
    embed.add_field(name='Lý do', value=reason, inline=True)
    embed.add_field(name='QTV', value=ctx.author.mention, inline=True)
    await ctx.reply(embed=embed)

# ==================== QTV: !ban ====================
@bot.command(name='ban')
async def cmd_ban(ctx: commands.Context, member: discord.Member = None, *, reason: str = 'Không có lý do'):
    if not is_qtv(ctx.author):
        return await ctx.reply('❌ Bạn không có quyền **QTV** để dùng lệnh này!')
    if not member:
        return await ctx.reply('❌ Sử dụng: `!ban @user [lý do]`')
    if not member.bannable:
        return await ctx.reply('❌ Không thể ban user này!')
    await member.ban(reason=reason)
    embed = discord.Embed(title='🔨 BAN USER', color=0x8B0000)
    embed.add_field(name='User', value=member.mention, inline=True)
    embed.add_field(name='Lý do', value=reason, inline=True)
    embed.add_field(name='QTV', value=ctx.author.mention, inline=True)
    await ctx.reply(embed=embed)

# ==================== QTV: !settien ====================
@bot.command(name='settien')
async def cmd_settien(ctx: commands.Context, user: discord.User = None, amount: int = None):
    if not is_qtv(ctx.author):
        return await ctx.reply('❌ Bạn không có quyền **QTV** để dùng lệnh này!')
    if not user or amount is None:
        return await ctx.reply('❌ Sử dụng: `!settien @user <số tiền>`')
    if amount < 0:
        return await ctx.reply('❌ Số tiền không được âm!')
    db = load_db()
    acc = get_account(str(user.id), db)
    acc['balance'] = amount
    save_db(db)
    embed = discord.Embed(title='💵 SET TIỀN TÀI KHOẢN', color=0xFFD700)
    embed.add_field(name='User', value=user.mention, inline=True)
    embed.add_field(name='Số tiền mới', value=fmt_money(amount), inline=True)
    embed.add_field(name='QTV', value=ctx.author.mention, inline=True)
    await ctx.reply(embed=embed)
# ==================== QTV: !resettuongtac ====================
@bot.command(name='resettuongtac')
async def cmd_resettuongtac(ctx: commands.Context, user: discord.User = None):
    if not is_qtv(ctx.author):
        return await ctx.reply('❌ Bạn không có quyền **QTV** để dùng lệnh này!')
    
    db = load_db()
    
    # Reset 1 người
    if user:
        if str(user.id) in db['interactions']:
            db['interactions'][str(user.id)] = 0
            save_db(db)
            embed = discord.Embed(title='🔄 RESET TƯƠNG TÁC', color=0xFF8C00)
            embed.add_field(name='User', value=user.mention, inline=True)
            embed.add_field(name='Kết quả', value='Đã reset về **0**', inline=True)
            embed.add_field(name='QTV', value=ctx.author.mention, inline=True)
            await ctx.reply(embed=embed)
        else:
            await ctx.reply(f'❌ {user.mention} chưa có dữ liệu tương tác!')
    
    # Reset toàn server
    else:
        db['interactions'] = {}
        save_db(db)
        embed = discord.Embed(title='🔄 RESET TƯƠNG TÁC TOÀN SERVER', color=0xFF4444)
        embed.description = '✅ Đã reset tương tác của **tất cả mọi người** về 0!'
        embed.set_footer(text=f'Thực hiện bởi {ctx.author.name}')
        await ctx.reply(embed=embed)
# ==================== !ping ====================
@bot.command(name='ping')
async def cmd_ping(ctx: commands.Context):
    if not is_qtv(ctx.author):
        return await ctx.reply('❌ Bạn không có quyền dùng lệnh này!')
    latency = round(bot.latency * 1000)
    if latency < 100:
        color = 0x00FF7F
        status = '🟢 Tốt'
    elif latency < 200:
        color = 0xFFD700
        status = '🟡 Bình thường'
    else:
        color = 0xFF4444
        status = '🔴 Chậm'
    embed = discord.Embed(title='🏓 PONG!', color=color)
    embed.add_field(name='📡 Độ trễ', value=f'**{latency}ms**', inline=True)
    embed.add_field(name='📶 Trạng thái', value=status, inline=True)
    embed.set_footer(text=f'Yêu cầu bởi {ctx.author.name}')
    await ctx.reply(embed=embed)

# ==================== !tinnhan ====================
@bot.command(name='tinnhan')
async def cmd_tinnhan(ctx: commands.Context, channel: discord.TextChannel = None, *, content: str = None):
    if not is_qtv(ctx.author):
        return await ctx.reply('❌ Bạn không có quyền dùng lệnh này!')
    if not channel or not content:
        return await ctx.reply(
            '❌ Sử dụng: `!tinnhan #kênh <nội dung tin nhắn>`\n'
            'VD: `!tinnhan #general Xin chào mọi người!`'
        )
    embed = discord.Embed(
        description=f'📢 {content}',
        color=0x5865F2
    )
    embed.set_author(
        name=f'Thông báo từ {ctx.author.name}',
        icon_url=ctx.author.display_avatar.url
    )
    embed.set_footer(text=f'Server: {ctx.guild.name}')
    embed.timestamp = discord.utils.utcnow()
    await channel.send(embed=embed)
    await ctx.reply(f'✅ Đã gửi tin nhắn đến {channel.mention}!')
    # Xoá lệnh gốc để server nhìn gọn hơn
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

# ==================== ERROR HANDLER ====================
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.reply('❌ Không tìm thấy user đó!')
    elif isinstance(error, commands.UserNotFound):
        await ctx.reply('❌ Không tìm thấy user đó!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f'❌ Thiếu tham số! Dùng `!list` để xem hướng dẫn.')
    elif isinstance(error, commands.BadArgument):
        await ctx.reply('❌ Tham số không hợp lệ!')

# ==================== RUN ====================
bot.run(TOKEN)

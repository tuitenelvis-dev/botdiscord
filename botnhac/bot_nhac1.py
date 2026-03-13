import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# ==================== CẤU HÌNH ====================
PREFIX = '>'
VOICE_CHANNEL_ID = 1474786871400861828   # Room 1 - tự động vào đây
TEXT_CHANNEL_NAME = 'nghe-nhạc'          # Chỉ nhận lệnh ở kênh này
TOKEN = os.environ.get('DISCORD_TOKEN_NHAC')

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'noplaylist': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android_music'],
        }
    },
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ==================== HELPER ====================
def fmt_duration(seconds):
    if not seconds:
        return '??:??'
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

def is_url(text):
    return text.startswith('http://') or text.startswith('https://')
from youtubesearchpython import VideosSearch

async def get_info(query):
    loop = asyncio.get_event_loop()

    # Nếu là URL thì dùng thẳng
    if is_url(query):
        if '&list=' in query:
            query = query.split('&list=')[0]
        search = query
    else:
        # Tìm bằng youtubesearchpython
        def search_yt():
            results = VideosSearch(query, limit=1).result()
            if not results['result']:
                raise Exception('Không tìm thấy bài hát!')
            return results['result'][0]['link']
        search = await loop.run_in_executor(None, search_yt)

    def extract():
        data = ytdl.extract_info(search, download=False)
        if 'entries' in data:
            entries = [e for e in data['entries'] if e]
            if not entries:
                raise Exception('Không tìm thấy!')
            return entries[0]
        return data

    return await loop.run_in_executor(None, extract)
# ==================== QUEUE ====================
queue = []
current = {}
is_playing = False
repeat = False      # lặp 1 bài
repeat_queue = False  # lặp cả queue

# ==================== BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ==================== AUTO RECONNECT KHI BỊ KICK ====================
@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and before.channel and not after.channel:
        # Bot bị kick hoặc disconnect
        await asyncio.sleep(3)
        guild = before.channel.guild
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if channel and not guild.voice_client:
            try:
                await channel.connect()
                print(f'✅ Tự reconnect vào {channel.name}')
            except Exception as e:
                print(f'❌ Lỗi reconnect: {e}')

# ==================== KIỂM TRA KÊNH ====================
def check_channel(ctx):
    return (
        ctx.channel.name.lower().replace(' ', '-') == 'nghe-nhạc' or
        ctx.channel.name.lower().replace(' ', '-') == 'nghe-nhac' or
        'nghe' in ctx.channel.name.lower()
    )

# ==================== READY ====================
@bot.event
async def on_ready():
    print(f'✅ Bot Nhạc 1 online: {bot.user}')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='>play <tên nhạc>'
    ))
    await asyncio.sleep(3)
    for guild in bot.guilds:
        # Thử dùng ID trước
        channel = guild.get_channel(VOICE_CHANNEL_ID)
        # Nếu không tìm được bằng ID thì tìm bằng tên
        if not channel:
            for vc in guild.voice_channels:
                if 'nghe' in vc.name.lower() or 'nhac' in vc.name.lower() or 'nhạc' in vc.name.lower():
                    channel = vc
                    break
        if channel:
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
                await asyncio.sleep(1)
            try:
                await channel.connect()
                print(f'✅ Đã vào phòng: {channel.name} (ID: {channel.id})')
            except Exception as e:
                print(f'❌ Lỗi vào phòng: {e}')
        else:
            print(f'❌ Không tìm thấy voice channel ID {VOICE_CHANNEL_ID}')
            print(f'📋 Các voice channel có: {[vc.name for vc in guild.voice_channels]}')

# ==================== AUTO RECONNECT ====================
async def ensure_voice(ctx):
    # Nếu đã kết nối và đang hoạt động thì OK
    if ctx.voice_client and ctx.voice_client.is_connected():
        return True

    # Thử disconnect cũ trước
    if ctx.voice_client:
        try:
            await ctx.voice_client.disconnect(force=True)
        except:
            pass
        await asyncio.sleep(2)

    # Kết nối lại
    channel = ctx.guild.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        return False
    try:
        await channel.connect(timeout=60, reconnect=False)
        await asyncio.sleep(2)  # chờ kết nối ổn định
        print(f'✅ Reconnected vào {channel.name}')
        return True
    except Exception as e:
        print(f'❌ Lỗi reconnect: {e}')
        return False

# ==================== PLAY NEXT ====================
async def play_next(ctx):
    global current, is_playing, repeat

    # Kiểm tra voice connection trước
    if not await ensure_voice(ctx):
        await ctx.send('❌ Bot bị mất kết nối voice, thử lại!')
        return

    # Lặp lại bài hiện tại
    if repeat and current:
        try:
            data = await get_info(current['url'])
            current['stream_url'] = data['url']
            source = discord.FFmpegPCMAudio(current['stream_url'], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.5)
            def after_play(error):
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            ctx.voice_client.play(source, after=after_play)
            return
        except Exception as e:
            print(f'Lỗi repeat: {e}')

    # Lặp queue
    if repeat_queue and current:
        queue.append(current)

    if not queue:
        is_playing = False
        current = {}
        embed = discord.Embed(description='✅ Hết nhạc trong danh sách!', color=0x5865F2)
        await ctx.send(embed=embed)
        return

    song = queue.pop(0)
    current = song
    is_playing = True

    try:
        # Lấy stream URL mới để tránh hết hạn
        data = await get_info(song['url'])
        song['stream_url'] = data['url']

        source = discord.FFmpegPCMAudio(song['stream_url'], **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=0.5)

        def after_play(error):
            if error:
                print(f'Lỗi phát nhạc: {error}')
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        ctx.voice_client.play(source, after=after_play)

        embed = discord.Embed(title='🎵 ĐANG PHÁT', color=0x1DB954)
        embed.add_field(name='Bài hát', value=f"[{song['title']}]({song['url']})", inline=False)
        embed.add_field(name='⏱ Thời lượng', value=fmt_duration(song['duration']), inline=True)
        embed.add_field(name='📋 Còn trong queue', value=f'{len(queue)} bài', inline=True)
        if repeat:
            embed.add_field(name='🔂 Repeat', value='Bật', inline=True)
        if song.get('thumbnail'):
            embed.set_thumbnail(url=song['thumbnail'])
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f'❌ Lỗi phát nhạc: `{e}`')
        await play_next(ctx)

# ==================== >play ====================
@bot.command(name='play', aliases=['p'])
async def cmd_play(ctx, *, query: str = None):
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')

    if not query:
        return await ctx.reply('❌ Sử dụng: `>play <tên bài hát hoặc link YouTube>`')

    # Bot tự vào voice nếu chưa vào
    if ctx.voice_client is None:
        channel = ctx.guild.get_channel(VOICE_CHANNEL_ID)
        if channel:
            await channel.connect()
        elif ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.reply('❌ Không tìm thấy voice channel!')

    msg = await ctx.reply('🔍 Đang tìm kiếm...')

    try:
        data = await get_info(query)
        song = {
            'title': data.get('title', 'Không rõ'),
            'url': data.get('webpage_url') or data.get('url') or query,
            'stream_url': data['url'],
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail', ''),
        }
    except Exception as e:
        return await msg.edit(content=f'❌ Không tìm thấy bài hát! `{e}`')

    queue.append(song)

    if not ctx.voice_client.is_playing():
        await msg.delete()
        await play_next(ctx)
    else:
        embed = discord.Embed(title='➕ ĐÃ THÊM VÀO QUEUE', color=0x5865F2)
        embed.add_field(name='Bài hát', value=f"[{song['title']}]({song['url']})", inline=False)
        embed.add_field(name='⏱ Thời lượng', value=fmt_duration(song['duration']), inline=True)
        embed.add_field(name='📋 Vị trí', value=f'#{len(queue)}', inline=True)
        if song.get('thumbnail'):
            embed.set_thumbnail(url=song['thumbnail'])
        await msg.edit(content=None, embed=embed)

# ==================== >addlist ====================
@bot.command(name='addlist', aliases=['al'])
async def cmd_addlist(ctx, *, query: str = None):
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')

    if not query:
        return await ctx.reply('❌ Sử dụng: `>addlist <tên bài hát>`')

    if ctx.voice_client is None:
        channel = ctx.guild.get_channel(VOICE_CHANNEL_ID)
        if channel:
            await channel.connect()

    msg = await ctx.reply(f'🔍 Đang tìm kiếm **{query}**...')

    try:
        data = await get_info(query)
        song = {
            'title': data.get('title', 'Không rõ'),
            'url': data.get('webpage_url') or data.get('url') or query,
            'stream_url': data['url'],
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail', ''),
        }
    except Exception as e:
        return await msg.edit(content=f'❌ Không tìm thấy! `{e}`')

    queue.append(song)
    embed = discord.Embed(title='✅ ĐÃ THÊM VÀO DANH SÁCH', color=0x00FF7F)
    embed.add_field(name='Bài hát', value=f"[{song['title']}]({song['url']})", inline=False)
    embed.add_field(name='⏱ Thời lượng', value=fmt_duration(song['duration']), inline=True)
    embed.add_field(name='📋 Vị trí', value=f'#{len(queue)}', inline=True)
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    await msg.edit(content=None, embed=embed)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

# ==================== >list ====================
@bot.command(name='list', aliases=['queue', 'q'])
async def cmd_list(ctx):
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')

    if not current and not queue:
        return await ctx.reply('📋 Danh sách nhạc đang trống!')

    embed = discord.Embed(title='📋 DANH SÁCH NHẠC - ROOM 1', color=0x5865F2)
    if current:
        repeat_str = ' 🔂' if repeat else ''
        embed.add_field(
            name=f'🎵 Đang phát{repeat_str}',
            value=f"[{current['title']}]({current['url']}) `{fmt_duration(current['duration'])}`",
            inline=False
        )
    if queue:
        lines = []
        for i, song in enumerate(queue[:10], 1):
            lines.append(f'`{i}.` [{song["title"]}]({song["url"]}) `{fmt_duration(song["duration"])}`')
        if len(queue) > 10:
            lines.append(f'... và **{len(queue) - 10}** bài nữa')
        embed.add_field(name=f'📝 Hàng chờ ({len(queue)} bài)', value='\n'.join(lines), inline=False)
    else:
        embed.add_field(name='📝 Hàng chờ', value='Trống', inline=False)

    embed.set_footer(text=f'Tổng: {len(queue) + (1 if current else 0)} bài | Prefix: {PREFIX}')
    await ctx.reply(embed=embed)

# ==================== >skip ====================
@bot.command(name='skip', aliases=['s'])
async def cmd_skip(ctx):
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        return await ctx.reply('❌ Không có nhạc đang phát!')
    ctx.voice_client.stop()
    await ctx.reply('⏭ Đã bỏ qua bài hát!')

# ==================== >stop ====================
@bot.command(name='stop')
async def cmd_stop(ctx):
    global is_playing, current, repeat, repeat_queue
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')
    queue.clear()
    current = {}
    is_playing = False
    repeat = False
    repeat_queue = False
    if ctx.voice_client:
        ctx.voice_client.stop()
    await ctx.reply('⏹ Đã dừng nhạc và xoá danh sách!')

# ==================== >repeat ====================
@bot.command(name='repeat', aliases=['r', 'loop'])
async def cmd_repeat(ctx, mode: str = None):
    global repeat, repeat_queue
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')

    if mode == 'queue' or mode == 'q':
        repeat_queue = not repeat_queue
        repeat = False
        status = '🔁 Bật' if repeat_queue else '⏹ Tắt'
        await ctx.reply(f'{status} lặp **cả danh sách**!')
    else:
        repeat = not repeat
        repeat_queue = False
        status = '🔂 Bật' if repeat else '⏹ Tắt'
        await ctx.reply(f'{status} lặp **bài hiện tại**!')

# ==================== >nowplaying ====================
@bot.command(name='nowplaying', aliases=['np'])
async def cmd_np(ctx):
    if not check_channel(ctx):
        return await ctx.reply(f'❌ Lệnh này chỉ dùng được trong kênh **NGHE NHẠC**!')
    if not current:
        return await ctx.reply('❌ Không có bài nào đang phát!')
    embed = discord.Embed(title='🎵 ĐANG PHÁT', color=0x1DB954)
    embed.add_field(name='Bài hát', value=f"[{current['title']}]({current['url']})", inline=False)
    embed.add_field(name='⏱ Thời lượng', value=fmt_duration(current['duration']), inline=True)
    embed.add_field(name='🔂 Repeat', value='Bật' if repeat else 'Tắt', inline=True)
    if current.get('thumbnail'):
        embed.set_thumbnail(url=current['thumbnail'])
    await ctx.reply(embed=embed)

# ==================== >help ====================
@bot.command(name='help')
async def cmd_help(ctx):
    embed = discord.Embed(title='🎵 BOT NHẠC 1 - HƯỚNG DẪN', color=0x1DB954)
    embed.add_field(
        name='Lệnh',
        value=(
            f'`{PREFIX}play <tên/link>` — Phát nhạc (tên hoặc link YouTube)\n'
            f'`{PREFIX}addlist <tên>` — Thêm bài vào danh sách\n'
            f'`{PREFIX}list` — Xem danh sách nhạc\n'
            f'`{PREFIX}skip` — Bỏ qua bài hiện tại\n'
            f'`{PREFIX}stop` — Dừng nhạc\n'
            f'`{PREFIX}repeat` — 🔂 Lặp bài hiện tại\n'
            f'`{PREFIX}repeat queue` — 🔁 Lặp cả danh sách\n'
            f'`{PREFIX}nowplaying` — Xem bài đang phát\n'
        ),
        inline=False
    )
    embed.set_footer(text='Room 1 | Chỉ dùng trong kênh NGHE NHẠC')
    await ctx.reply(embed=embed)

# ==================== RUN ====================
bot.run(TOKEN)
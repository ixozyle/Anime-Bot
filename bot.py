import os
import logging
import aiohttp
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
SHIKIMORI_API = "https://shikimori.one/api"
user_data = {}

LANGUAGES = {
    'ru': {
        'main_menu': '╔═══════════════════════╗\n║   🎭 ANIME SEARCH BOT   ║\n╚═══════════════════════╝\n\n🌐 Язык: Русский 🇷🇺',
        'search_btn': '🔍 Поиск аниме', 'top_btn': '🔥 Топ аниме', 'random_btn': '🎲 Случайное',
        'favorites_btn': '⭐ Избранное', 'settings_btn': '⚙️ Настройки', 'about_btn': 'ℹ️ О боте',
        'search_prompt': '🔍 Введите название аниме:', 'no_results': '❌ Ничего не найдено.',
        'loading': '⏳ Загружаю...', 'error': '❌ Ошибка. Попробуйте позже.',
        'add_favorite': '⭐ В избранное', 'remove_favorite': '💔 Убрать', 'back': '🔙 Назад',
        'more_info': 'ℹ️ Подробнее', 'characters': '👥 Персонажи', 'episodes': 'эп.',
        'rating': '⭐ Рейтинг', 'genres': '🎭 Жанры', 'description': '📖 Описание',
        'main_chars': '👥 Главные персонажи', 'sources': '🔗 Источники',
        'added_to_fav': '✅ Добавлено!', 'removed_from_fav': '✅ Убрано!',
        'empty_favorites': '📭 Избранное пусто.', 'welcome': '👋 Привет! Я помогу найти аниме.',
    },
    'en': {
        'main_menu': '╔═══════════════════════╗\n║   🎭 ANIME SEARCH BOT   ║\n╚═══════════════════════╝\n\n🌐 Language: English 🇬🇧',
        'search_btn': '🔍 Search anime', 'top_btn': '🔥 Top anime', 'random_btn': '🎲 Random',
        'favorites_btn': '⭐ Favorites', 'settings_btn': '⚙️ Settings', 'about_btn': 'ℹ️ About',
        'search_prompt': '🔍 Enter anime title:', 'no_results': '❌ Nothing found.',
        'loading': '⏳ Loading...', 'error': '❌ Error. Try later.',
        'add_favorite': '⭐ Add', 'remove_favorite': '💔 Remove', 'back': '🔙 Back',
        'more_info': 'ℹ️ More', 'characters': '👥 Characters', 'episodes': 'eps',
        'rating': '⭐ Rating', 'genres': '🎭 Genres', 'description': '📖 Description',
        'main_chars': '👥 Main characters', 'sources': '🔗 Sources',
        'added_to_fav': '✅ Added!', 'removed_from_fav': '✅ Removed!',
        'empty_favorites': '📭 Favorites empty.', 'welcome': '👋 Hello! I help find anime.',
    }
}

def t(uid, key):
    lang = user_data.get(uid, {}).get('lang', 'ru')
    return LANGUAGES[lang].get(key, key)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_data:
        user_data[uid] = {'lang': 'ru', 'favorites': []}
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton(t(uid, 'search_btn'), callback_data='search')],
        [InlineKeyboardButton(t(uid, 'top_btn'), callback_data='top'),
         InlineKeyboardButton(t(uid, 'random_btn'), callback_data='random')],
        [InlineKeyboardButton(t(uid, 'favorites_btn'), callback_data='favorites')],
        [InlineKeyboardButton(t(uid, 'settings_btn'), callback_data='settings'),
         InlineKeyboardButton(t(uid, 'about_btn'), callback_data='about')],
        [InlineKeyboardButton('🇷🇺 RU', callback_data='lang_ru'),
         InlineKeyboardButton('🇬🇧 EN', callback_data='lang_en')]
    ]
    text = t(uid, 'main_menu') + '\n\n' + t(uid, 'welcome')
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def search_anime(query, limit=10):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{SHIKIMORI_API}/animes"
            params = {'search': query, 'limit': limit, 'order': 'popularity'}
            async with session.get(url, params=params) as resp:
                return await resp.json() if resp.status == 200 else []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

async def get_details(aid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHIKIMORI_API}/animes/{aid}") as resp:
                return await resp.json() if resp.status == 200 else None
    except Exception as e:
        logger.error(f"Details error: {e}")
        return None

async def get_characters(aid):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHIKIMORI_API}/animes/{aid}/roles") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [c for c in data if c.get('roles') and 'Main' in c['roles']][:6]
                return []
    except Exception as e:
        logger.error(f"Characters error: {e}")
        return []

def format_card(anime, uid):
    title_ru = anime.get('russian', 'N/A')
    title_en = anime.get('name', 'N/A')
    title_jp = anime.get('japanese', ['N/A'])[0] if anime.get('japanese') else 'N/A'
    score = anime.get('score', 'N/A')
    episodes = anime.get('episodes') or '?'
    duration = anime.get('duration', 'N/A')
    status = anime.get('status', 'N/A')
    status_emoji = {'ongoing': '🟢', 'released': '🔵', 'anons': '🟡'}.get(status, '⚪')
    year = (anime.get('aired_on', '') or 'N/A').split('-')[0]
    genres = ', '.join([g.get('russian', g.get('name', '')) for g in anime.get('genres', [])]) or 'N/A'
    desc = anime.get('description', 'Нет описания')
    if len(desc) > 300:
        desc = desc[:297] + '...'
    
    text = f"「 {title_ru} 」\n🇬🇧 {title_en}\n🇯🇵 {title_jp}\n\n"
    text += f"⭐ {t(uid, 'rating')}:\n├ Shikimori: {score}\n└ MyAnimeList: {score}\n\n"
    text += f"📺 {episodes} {t(uid, 'episodes')} | ⏱️ {duration} мин\n"
    text += f"📅 {year} | {status_emoji} {status.title()}\n\n"
    text += f"🎭 {t(uid, 'genres')}: {genres}\n\n"
    text += f"📖 {t(uid, 'description')}:\n{desc}"
    return text

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    data = query.data
    
    if data == 'menu':
        await show_main_menu(update, context)
    elif data == 'search':
        await query.edit_message_text(t(uid, 'search_prompt'))
        context.user_data['waiting_search'] = True
    elif data == 'top':
        await query.edit_message_text(t(uid, 'loading'))
        results = await search_anime('', limit=10)
        await show_results(update, context, results) if results else await query.edit_message_text(t(uid, 'error'))
    elif data == 'random':
        await query.edit_message_text(t(uid, 'loading'))
        results = await search_anime('', limit=50)
        if results:
            await show_card(update, context, random.choice(results)['id'])
        else:
            await query.edit_message_text(t(uid, 'error'))
    elif data == 'favorites':
        favs = user_data.get(uid, {}).get('favorites', [])
        if not favs:
            kb = [[InlineKeyboardButton(t(uid, 'back'), callback_data='menu')]]
            await query.edit_message_text(t(uid, 'empty_favorites'), reply_markup=InlineKeyboardMarkup(kb))
        else:
            text = f"⭐ {t(uid, 'favorites_btn')}:\n\n"
            kb = [[InlineKeyboardButton(f"Anime #{fid}", callback_data=f'anime_{fid}')] for fid in favs[:10]]
            kb.append([InlineKeyboardButton(t(uid, 'back'), callback_data='menu')])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data == 'settings':
        kb = [[InlineKeyboardButton('🇷🇺 Русский', callback_data='lang_ru')],
              [InlineKeyboardButton('🇬🇧 English', callback_data='lang_en')],
              [InlineKeyboardButton(t(uid, 'back'), callback_data='menu')]]
        await query.edit_message_text(t(uid, 'settings_btn'), reply_markup=InlineKeyboardMarkup(kb))
    elif data == 'about':
        text = "🎭 Anime Search Bot\n\nБот для поиска аниме.\n\n📊 Источники:\n• Shikimori\n• MyAnimeList\n\nСоздано с ❤️"
        kb = [[InlineKeyboardButton(t(uid, 'back'), callback_data='menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith('lang_'):
        user_data[uid]['lang'] = data.split('_')[1]
        await show_main_menu(update, context)
    elif data.startswith('anime_'):
        await show_card(update, context, data.split('_')[1])
    elif data.startswith('fav_add_'):
        aid = int(data.split('_')[2])
        if uid not in user_data:
            user_data[uid] = {'lang': 'ru', 'favorites': []}
        if aid not in user_data[uid]['favorites']:
            user_data[uid]['favorites'].append(aid)
        await query.answer(t(uid, 'added_to_fav'))
        await show_card(update, context, aid)
    elif data.startswith('fav_remove_'):
        aid = int(data.split('_')[2])
        if uid in user_data and aid in user_data[uid]['favorites']:
            user_data[uid]['favorites'].remove(aid)
        await query.answer(t(uid, 'removed_from_fav'))
        await show_card(update, context, aid)
    elif data.startswith('chars_'):
        await show_chars(update, context, data.split('_')[1])
    elif data.startswith('info_'):
        await show_info(update, context, data.split('_')[1])

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results):
    uid = update.effective_user.id
    text = f"🔍 Найдено: {len(results)}\n"
    kb = []
    for a in results[:10]:
        title = a.get('russian') or a.get('name', 'Unknown')
        year = (a.get('aired_on', '') or '?')[:4]
        score = a.get('score', '?')
        kb.append([InlineKeyboardButton(f"{title} ({year}) ⭐{score}", callback_data=f"anime_{a['id']}")])
    kb.append([InlineKeyboardButton(t(uid, 'back'), callback_data='menu')])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def show_card(update: Update, context: ContextTypes.DEFAULT_TYPE, aid):
    uid = update.effective_user.id
    query = update.callback_query
    await query.edit_message_text(t(uid, 'loading'))
    anime = await get_details(aid)
    if not anime:
        await query.edit_message_text(t(uid, 'error'))
        return
    text = format_card(anime, uid)
    is_fav = aid in user_data.get(uid, {}).get('favorites', [])
    fav_txt = t(uid, 'remove_favorite') if is_fav else t(uid, 'add_favorite')
    fav_cb = f'fav_remove_{aid}' if is_fav else f'fav_add_{aid}'
    kb = [[InlineKeyboardButton(t(uid, 'characters'), callback_data=f'chars_{aid}'),
           InlineKeyboardButton(t(uid, 'more_info'), callback_data=f'info_{aid}')],
          [InlineKeyboardButton(fav_txt, callback_data=fav_cb)],
          [InlineKeyboardButton(t(uid, 'back'), callback_data='menu')]]
    img = f"https://shikimori.one{anime['image']['original']}" if anime.get('image') else None
    try:
        if img:
            await query.message.delete()
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img, caption=text,
                                        reply_markup=InlineKeyboardMarkup(kb))
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    except:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def show_chars(update: Update, context: ContextTypes.DEFAULT_TYPE, aid):
    uid = update.effective_user.id
    query = update.callback_query
    await query.edit_message_text(t(uid, 'loading'))
    chars = await get_characters(aid)
    if not chars:
        kb = [[InlineKeyboardButton(t(uid, 'back'), callback_data=f'anime_{aid}')]]
        await query.edit_message_text("Персонажи не найдены", reply_markup=InlineKeyboardMarkup(kb))
        return
    media = []
    for c in chars[:5]:
        ci = c.get('character', {})
        pi = c.get('person', {})
        cn = ci.get('russian') or ci.get('name', 'Unknown')
        pn = pi.get('russian') or pi.get('name', 'Unknown')
        img = f"https://shikimori.one{ci['image']['original']}" if ci.get('image') else None
        if img:
            media.append(InputMediaPhoto(media=img, caption=f"💫 {cn}\n🎙️ {pn}" if len(media) == 0 else None))
    try:
        await query.message.delete()
        if media:
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media)
        kb = [[InlineKeyboardButton(t(uid, 'back'), callback_data=f'anime_{aid}')]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"👥 {t(uid, 'main_chars')}",
                                      reply_markup=InlineKeyboardMarkup(kb))
    except:
        kb = [[InlineKeyboardButton(t(uid, 'back'), callback_data=f'anime_{aid}')]]
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ошибка",
                                      reply_markup=InlineKeyboardMarkup(kb))

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE, aid):
    uid = update.effective_user.id
    anime = await get_details(aid)
    if not anime:
        await update.callback_query.answer(t(uid, 'error'))
        return
    text = f"📊 {t(uid, 'more_info')}\n\n🔗 {t(uid, 'sources')}:\n• Shikimori: https://shikimori.one/animes/{aid}\n\n"
    text += f"📈 Популярность: #{anime.get('popularity', 'N/A')}\n"
    if anime.get('studios'):
        text += f"🎬 Студия: {', '.join([s['name'] for s in anime['studios']])}\n"
    text += f"📺 Тип: {anime.get('kind', 'N/A').upper()}\n🔞 Возраст: {anime.get('rating', 'N/A')}"
    kb = [[InlineKeyboardButton(t(uid, 'back'), callback_data=f'anime_{aid}')]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if context.user_data.get('waiting_search'):
        context.user_data['waiting_search'] = False
        query_text = update.message.text
        await update.message.reply_text(t(uid, 'loading'))
        results = await search_anime(query_text)
        if results:
            text = f"🔍 Найдено: {len(results)}\n"
            kb = []
            for a in results[:10]:
                title = a.get('russian') or a.get('name', 'Unknown')
                year = (a.get('aired_on', '') or '?')[:4]
                score = a.get('score', '?')
                kb.append([InlineKeyboardButton(f"{title} ({year}) ⭐{score}", callback_data=f"anime_{a['id']}")])
            kb.append([InlineKeyboardButton(t(uid, 'back'), callback_data='menu')])
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text(t(uid, 'no_results'))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

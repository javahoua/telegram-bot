import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import os
from datetime import datetime
import jdatetime

# تنظیم لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات
TOKEN =os.getenv("7774570069:AAHBlnCoyIFN0Dp5HYsW2kvzp-YxBvX5cx8")


# آدرس API
API_URL = "https://jsp5.ir/onlineapi/Travels"

# مسیرهای مجاز
ROUTES = [
    ("هرمز", "بندرعباس"),
    ("هرمز", "قشم"),
    ("بندرعباس", "قشم"),
    ("بندرعباس", "هرمز")
]

def convert_to_jalali(date_str: str) -> str:
    """تبدیل تاریخ میلادی به شمسی"""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        jalali_date = jdatetime.date.fromgregorian(date=dt.date())
        return jalali_date.strftime("%Y/%m/%d")
    except ValueError:
        return "📅 تاریخ نامعتبر"

def format_time(time_str: str) -> str:
    """فرمت کردن ساعت"""
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except ValueError:
        return "⏰ ساعت نامعتبر"

def create_main_menu() -> ReplyKeyboardMarkup:
    """ایجاد منوی اصلی با چیدمان دوتایی"""
    keyboard = [
        [f"{origin}-{destination}" for origin, destination in ROUTES[i:i+2]]
        for i in range(0, len(ROUTES), 2)
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def create_sub_menu(path: str) -> ReplyKeyboardMarkup:
    """ایجاد زیرمنو برای مسیر انتخاب‌شده"""
    keyboard = [
        [f"همه سفرهای {path}", f"مسافرگیری {path}"],
        ["انتخاب شناور", "🔙 بازگشت به منو"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def create_ship_menu(ships: list) -> ReplyKeyboardMarkup:
    """ایجاد منو برای انتخاب شناور"""
    keyboard = [[ship for ship in ships[i:i+2]] for i in range(0, len(ships), 2)]
    keyboard.append(["🔙 بازگشت به منو"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال پیام خوش‌آمدگویی"""
    # حذف پیام قبلی اگر وجود داشته باشد
    if 'last_message_id' in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=context.user_data['last_message_id']
            )
        except Exception as e:
            logger.warning(f"خطا در حذف پیام قبلی در start: {e}")

    message = await update.message.reply_text(
        "🌊 به ربات سفرهای دریایی خوش آمدید!\nاز منوی پایین مسیر را انتخاب کنید:",
        reply_markup=create_main_menu()
    )
    context.user_data['last_message_id'] = message.message_id
    context.user_data['state'] = 'main_menu'

async def travels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی اصلی"""
    # حذف پیام قبلی اگر وجود داشته باشد
    if 'last_message_id' in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=context.user_data['last_message_id']
            )
        except Exception as e:
            logger.warning(f"خطا در حذف پیام قبلی در travels: {e}")

    message = await update.message.reply_text(
        "🛳️ مسیر را از منوی پایین انتخاب کنید:",
        reply_markup=create_main_menu()
    )
    context.user_data['last_message_id'] = message.message_id
    context.user_data['state'] = 'main_menu'

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مدیریت انتخاب‌های کاربر از منوی درختی"""
    user_input = update.message.text
    state = context.user_data.get('state', 'main_menu')

    # حذف پیام قبلی اگر وجود داشته باشد
    if 'last_message_id' in context.user_data:
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=context.user_data['last_message_id']
            )
        except Exception as e:
            logger.warning(f"خطا در حذف پیام قبلی در handle_menu_selection: {e}")

    try:
        # درخواست به API
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        travels = response.json()

        # بررسی لیست بودن داده‌ها
        if not isinstance(travels, list):
            message = await update.message.reply_text(
                "❌ فرمت داده‌های API پشتیبانی نمی‌شود.",
                reply_markup=create_main_menu()
            )
            context.user_data['last_message_id'] = message.message_id
            context.user_data['state'] = 'main_menu'
            logger.error("داده‌های API لیست نیستند.")
            return

        # لاگ کردن مسیرهای موجود برای دیباگ
        paths = [travel.get("path", "نامعلوم") for travel in travels]
        logger.info(f"مسیرهای موجود در API: {paths}")

        # مدیریت منوی درختی
        if user_input == "🔙 بازگشت به منو":
            message = await update.message.reply_text(
                "🛳️ مسیر را از منوی پایین انتخاب کنید:",
                reply_markup=create_main_menu()
            )
            context.user_data['last_message_id'] = message.message_id
            context.user_data['state'] = 'main_menu'
            return

        if state == 'main_menu':
            # مرحله 1: انتخاب مسیر
            if user_input in [f"{origin}-{destination}" for origin, destination in ROUTES]:
                context.user_data['selected_path'] = user_input
                expected_path = user_input.replace("-", " به ")
                message = await update.message.reply_text(
                    f"🌍 مسیر {expected_path} انتخاب شد. گزینه را انتخاب کنید:",
                    reply_markup=create_sub_menu(user_input)
                )
                context.user_data['last_message_id'] = message.message_id
                context.user_data['state'] = 'sub_menu'
                return

        elif state == 'sub_menu':
            selected_path = context.user_data.get('selected_path', '')
            expected_path = selected_path.replace("-", " به ").lower().strip()

            if user_input == f"همه سفرهای {selected_path}":
                # فیلتر همه سفرها برای مسیر
                filtered_travels = [
                    travel for travel in travels
                    if travel.get("path", "").lower().strip().replace(" ", " ") == expected_path
                ]
            elif user_input == f"مسافرگیری {selected_path}":
                # فیلتر مسافرگیری برای مسیر
                filtered_travels = [
                    travel for travel in travels
                    if travel.get("path", "").lower().strip().replace(" ", " ") == expected_path
                    and travel.get("stat", "").lower().strip() == "مسافرگیری"
                ]
            elif user_input == "انتخاب شناور":
                # نمایش منوی شناورها
                ships = sorted(set(
                    travel.get("ship", "نامعلوم")
                    for travel in travels
                    if travel.get("path", "").lower().strip().replace(" ", " ") == expected_path
                ))
                if not ships:
                    message = await update.message.reply_text(
                        f"⚠️ هیچ شناوری برای {expected_path} یافت نشد!",
                        reply_markup=create_sub_menu(selected_path)
                    )
                    context.user_data['last_message_id'] = message.message_id
                    context.user_data['state'] = 'sub_menu'
                    return
                message = await update.message.reply_text(
                    f"🚤 شناور را برای {expected_path} انتخاب کنید:",
                    reply_markup=create_ship_menu(ships)
                )
                context.user_data['last_message_id'] = message.message_id
                context.user_data['state'] = 'ship_menu'
                return
            else:
                # ورودی نامعتبر
                message = await update.message.reply_text(
                    f"❌ گزینه نامعتبر! لطفاً از منو انتخاب کنید:",
                    reply_markup=create_sub_menu(selected_path)
                )
                context.user_data['last_message_id'] = message.message_id
                context.user_data['state'] = 'sub_menu'
                return

        elif state == 'ship_menu':
            # فیلتر بر اساس شناور
            selected_path = context.user_data.get('selected_path', '')
            expected_path = selected_path.replace("-", " به ").lower().strip()
            filtered_travels = [
                travel for travel in travels
                if travel.get("path", "").lower().strip().replace(" ", " ") == expected_path
                and travel.get("ship", "").lower().strip() == user_input.lower().strip()
            ]
            # بازگشت به زیرمنو
            context.user_data['state'] = 'sub_menu'

        # نمایش نتایج
        if not filtered_travels:
            logger.info(f"هیچ سفری برای {user_input} یافت نشد. مسیر: {expected_path}")
            message = await update.message.reply_text(
                f"⚠️ هیچ سفری با این شرایط یافت نشد!\nمسیرهای موجود: {', '.join(set(paths))}",
                reply_markup=create_sub_menu(selected_path)
            )
            context.user_data['last_message_id'] = message.message_id
            return

        message_text = "🛳️ سفرهای موجود:\n\n"
        for travel in filtered_travels[:5]: # محدود به ۵ مورد
            path = travel.get("path", "نامعلوم")
            date = convert_to_jalali(travel.get("boarding", "نامعتبر"))
            time = format_time(travel.get("boarding", "نامعتبر"))
            status = travel.get("stat", "نامعلوم")
            ship = travel.get("ship", "نامعلوم")
            capacity = travel.get("cap", "نامعلوم")
            tickets = travel.get("tickets", "نامعلوم")
            message_text += (
                f"🌍 **{path}**\n"
                f"📅 تاریخ: {date}\n"
                f"⏰ ساعت: {time}\n"
                f"🚤 شناور: {ship}\n"
                f"👥 ظرفیت: {capacity}\n"
                f"🎫 بلیط‌ها: {tickets}\n"
                f"📊 وضعیت: {status}\n"
                "─────────────────\n"
            )

        message = await update.message.reply_text(
            message_text,
            reply_markup=create_sub_menu(selected_path),
            parse_mode="Markdown"
        )
        context.user_data['last_message_id'] = message.message_id

    except requests.exceptions.RequestException as e:
        logger.error(f"خطا در درخواست API: {e}")
        message = await update.message.reply_text(
            "❌ خطا در دریافت داده از API. لطفاً دوباره امتحان کنید.",
            reply_markup=create_main_menu()
        )
        context.user_data['last_message_id'] = message.message_id
        context.user_data['state'] = 'main_menu'
    except ValueError as e:
        logger.error(f"خطا در پردازش JSON: {e}")
        message = await update.message.reply_text(
            "❌ خطا در پردازش داده. فرمت داده نادرست است.",
            reply_markup=create_main_menu()
        )
        context.user_data['last_message_id'] = message.message_id
        context.user_data['state'] = 'main_menu'

def main() -> None:
    """اجرای ربات"""
    application = Application.builder().token(TOKEN).build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("travels", travels))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection))

    # شروع ربات
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

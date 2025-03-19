# bot.py
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import uuid

# Конфигурация
BOT_TOKEN = "7597499330:AAFV_qzG1EpcW6cxN-MY2ZJwcwVQWJFL9GQ"  # Токен бота
ADMIN_IDS = [1089550963]  # ID администраторов

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# Логирование
logging.basicConfig(level=logging.INFO)

# База данных (SQLite + SQLAlchemy)
Base = declarative_base()
engine = create_engine('sqlite:///bot.db')
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    trial_key = Column(String, unique=True)
    subscription_active = Column(Boolean, default=False)
    trial_expires = Column(DateTime)
    referral_code = Column(String)
    referred_by = Column(String)
    subscription_end = Column(DateTime)

def create_db():
    Base.metadata.create_all(engine)

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Подписка"), KeyboardButton(text="Рефералы")],
        [KeyboardButton(text="Помощь"), KeyboardButton(text="О сервисе")],
        [KeyboardButton(text="Главное меню")]
    ],
    resize_keyboard=True
)

subscription_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Продлить", callback_data="renew_subscription")],
        [InlineKeyboardButton(text="Проверить статус", callback_data="check_status")],
        [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")]
    ]
)

# Вспомогательные функции
def generate_trial_key():
    return str(uuid.uuid4())

def generate_referral_link(user_id):
    return f"https://t.me/your_bot_name?start={user_id}"

# Тексты на русском языке
MESSAGES = {
    "welcome": "Добро пожаловать! Ваш пробный ключ: {trial_key}\nИспользуйте /referral для рефералов.",
    "welcome_back": "С возвращением!",
    "subscription_active": "Ваша подписка активна до {end_date}.",
    "subscription_inactive": "Подписка неактивна.",
    "not_admin": "Вы не администратор.",
    "faq": "FAQ:\n1. Как получить пробный период? Используйте /start\n2. Как продлить подписку? Используйте /subscription\n3. Реферальная система? Используйте /referral\n4. О сервисе? Используйте /info",
    "about_service": "О сервисе:\nЭтот бот предоставляет доступ к платному контенту.\nВы можете использовать пробный период или приобрести подписку.",
    "referral_info": "Ваша реферальная ссылка: {referral_link}\nПриглашено пользователей: {invited_count}",
    "error_try_again": "Что-то пошло не так. Попробуйте позже.",
    "main_menu": "Вы в главном меню."
}

# Обработчики команд
@router.message(Command("start"))
async def start_handler(message: Message):
    user_id = str(message.from_user.id)
    session = Session()
    
    # Проверяем/создаем пользователя
    user = session.get(User, user_id)
    if not user:
        trial_key = generate_trial_key()
        new_user = User(
            id=user_id,
            trial_key=trial_key,
            trial_expires=datetime.now() + timedelta(days=7),
            referral_code=generate_referral_link(user_id)
        )
        session.add(new_user)
        session.commit()
        
        await message.answer(
            MESSAGES["welcome"].format(trial_key=trial_key),
            reply_markup=main_keyboard
        )
    else:
        await message.answer(MESSAGES["welcome_back"], reply_markup=main_keyboard)
        
    session.close()

@router.message(F.text == "Подписка")  # Обработка кнопки "Подписка"
async def subscription_button_handler(message: Message):
    await subscription_handler(message)

@router.message(F.text == "Рефералы")  # Обработка кнопки "Рефералы"
async def referral_button_handler(message: Message):
    await referral_handler(message)

@router.message(F.text == "Помощь")  # Обработка кнопки "Помощь"
async def help_button_handler(message: Message):
    await help_handler(message)

@router.message(F.text == "О сервисе")  # Обработка кнопки "О сервисе"
async def about_button_handler(message: Message):
    await info_handler(message)

@router.message(F.text == "Главное меню")  # Возврат в главное меню
async def main_menu_handler(message: Message):
    await message.answer(MESSAGES["main_menu"], reply_markup=main_keyboard)

@router.callback_query(F.data == "main_menu")  # Возврат в главное меню через callback
async def main_menu_callback(callback: CallbackQuery):
    await callback.message.answer(MESSAGES["main_menu"], reply_markup=main_keyboard)
    await callback.answer()

@router.message(Command("subscription"))
async def subscription_handler(message: Message):
    user_id = str(message.from_user.id)
    session = Session()
    user = session.get(User, user_id)
    
    if user.subscription_active and user.subscription_end > datetime.now():
        await message.answer(MESSAGES["subscription_active"].format(end_date=user.subscription_end))
    else:
        await message.answer(MESSAGES["subscription_inactive"], reply_markup=subscription_keyboard)
    
    session.close()

@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(MESSAGES["faq"])

@router.message(Command("info"))
async def info_handler(message: Message):
    await message.answer(MESSAGES["about_service"])

@router.message(Command("referral"))
async def referral_handler(message: Message):
    user_id = str(message.from_user.id)
    session = Session()
    user = session.get(User, user_id)
    
    if user:
        invited_count = session.query(User).filter_by(referred_by=user_id).count()
        await message.answer(
            MESSAGES["referral_info"].format(referral_link=user.referral_code, invited_count=invited_count)
        )
    else:
        await message.answer(MESSAGES["error_try_again"])
    
    session.close()

@router.callback_query(F.data == "renew_subscription")
async def renew_subscription(callback: CallbackQuery):
    await callback.message.answer("Чтобы продлить подписку, свяжитесь с поддержкой.")
    await callback.answer()

@router.callback_query(F.data == "check_status")
async def check_status(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    session = Session()
    user = session.get(User, user_id)
    
    if user.subscription_active and user.subscription_end > datetime.now():
        await callback.message.answer(MESSAGES["subscription_active"].format(end_date=user.subscription_end))
    else:
        await callback.message.answer(MESSAGES["subscription_inactive"])
    
    session.close()
    await callback.answer()

# Админ-команды
@router.message(Command("admin"))
async def admin_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(MESSAGES["not_admin"])
        return
    
    session = Session()
    users = session.query(User).all()
    stats = "\n".join([f"{user.id}: {'Active' if user.subscription_active else 'Inactive'}" for user in users])
    await message.answer(stats)
    session.close()

# Главная функция
async def main():
    create_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
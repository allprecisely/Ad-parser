from typing import Optional
from storage import Storage
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

from settings import *

DEFAULT_TYPE = ContextTypes.DEFAULT_TYPE
BACK = 'back to menu'
SAVE = 'save'
SAVE_PREFIX = 'Current parameters are:'
COMMON_BUTTONS = [
    [KeyboardButton('Choose city'), KeyboardButton('Choose radius')],
    [KeyboardButton('Choose price_min'), KeyboardButton('Choose price_max')],
]
RENT_BUTTONS = COMMON_BUTTONS + [
    [KeyboardButton('Choose area_min'), KeyboardButton('Choose area_max')],
    [KeyboardButton('Choose bedrooms'), KeyboardButton('Choose furnishing')],
    [KeyboardButton('Choose pets'), KeyboardButton('Choose excluded_words')],
    [KeyboardButton(SAVE), KeyboardButton(BACK)],
]
MOTORBIKES_BUTTONS = COMMON_BUTTONS + [
    [KeyboardButton('Choose mileage_min'), KeyboardButton('Choose mileage_max')],
    [KeyboardButton('Choose types'), KeyboardButton('Choose excluded_words')],
    [KeyboardButton(SAVE), KeyboardButton(BACK)],
]
CARS_BUTTONS = COMMON_BUTTONS + [
    [KeyboardButton('Choose mileage_min'), KeyboardButton('Choose mileage_max')],
    [KeyboardButton('Choose year_min'), KeyboardButton('Choose year_max')],
    [KeyboardButton('Choose gearbox'), KeyboardButton('Choose excluded_words')],
    [KeyboardButton(SAVE), KeyboardButton(BACK)],
]

BEFORE_START_TEXT = '''
Hello! I can find new ads about rent house/flat or buying car/motorbike on Cyprus.
For start searching, press Start and put cryterias.
'''
CHOOSE_CATEGORY_TEXT = (
    'You should choose at least any city and the radius to start polling ads.'
)
WELKOM_TEXT = 'Welcome to search bot! Choose search category.'
EXCLUDED_WORDS_TEXT = 'Please input comma separted words. If any of them are in title, ad will be ignored.'

TG_CATEGORIES = {
    CATEGORY_RENT: {'title': f'{CATEGORY_RENT} 🏘', 'buttons': RENT_BUTTONS},
    CATEGORY_MOTORBIKES: {
        'title': f'{CATEGORY_MOTORBIKES} �',
        'buttons': MOTORBIKES_BUTTONS,
    },
    CATEGORY_CARS: {'title': f'{CATEGORY_CARS} 🚗', 'buttons': CARS_BUTTONS},
}


class TgUpdater:
    def __init__(self) -> None:
        self.application = ApplicationBuilder().token(TOKEN).build()
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CallbackQueryHandler(self.button))
        self.application.add_handler(MessageHandler(filters.TEXT, self.setup))

        self.storage = Storage()

    def run(self) -> None:
        self.application.run_polling()

    async def start(
        self, update: Update, context: DEFAULT_TYPE, text: str = WELKOM_TEXT
    ):
        buttons = [[KeyboardButton(x['title'])] for x in TG_CATEGORIES.values()]

        existance = await self.handle_existance(update, context)
        if existance is not None:
            buttons.append([KeyboardButton('current search parameters 📒')])
            txt = 'run searching 🟢'
            if existance:
                txt = 'stop searching ⛔️'
            buttons.append([KeyboardButton(txt)])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=ReplyKeyboardMarkup(buttons),
        )

    async def handle_existance(self, update: Update, context: DEFAULT_TYPE) -> Optional[str]:
        is_user_existed_and_active = self.storage.is_user_existed_and_active(
            update.effective_user.id
        )
        if is_user_existed_and_active is not None:
            if not any(category in context.user_data for category in TG_CATEGORIES):
                for (
                    category_name,
                    category_props,
                ) in self.storage.ad_params_by_user(update.effective_user.id).items():
                    if not category_props:
                        continue
                    context.user_data[category_name] = {**category_props, 'saved': True}
            context.user_data['user_exists'] = True
        return is_user_existed_and_active

    async def setup(self, update: Update, context: DEFAULT_TYPE):
        msg = update.effective_message.text
        category = context.user_data.get('category')
        last_action = context.user_data.get('last_action')

        if msg == BACK:
            context.user_data['last_action'] = None
            return await self.start(update, context, 'Choose category')

        if msg == 'run searching 🟢':
            await self.start(update, context, 'Searching started.')
            return self.storage.set_user_status(update.effective_user.id, True)
        if msg == 'stop searching ⛔️':
            await self.start(update, context, 'Searching stopped.')
            return self.storage.set_user_status(update.effective_user.id, False)
        if msg == 'current search parameters 📒':
            if not category:
                await self.handle_existance(update, context)
            text = ''
            for tg_category in TG_CATEGORIES:
                if 'saved' in context.user_data.get(tg_category, {}):
                        txt_props = '\n'.join(
                            f'{k}: {v}' for k, v in context.user_data[tg_category].items()
                            if v and k != 'saved' and k != 'id'
                        )
                        text += f'{tg_category} parameters are:\n{txt_props}\n\n'
            return await update.message.reply_text(text)

        if not context.user_data.get('last_action'):
            return await self.handle_choose(update, context, msg)

        if not (last_action and category):
            return await self.start(
                update, context, 'Unknown last_action. Please start again'
            )

        if msg == SAVE:
            return await self.handle_save(update, context)

        if msg.startswith('Choose'):
            await self.update_checkbox(update, context)
            field = msg[len('Choose ') :]
            if 'min' in field or 'max' in field or field == 'radius':
                msg_obj = await update.message.reply_text(
                    f'Please type value for {field}'
                )
            elif field in CHECKBOX:
                selected = context.user_data[category].get(field, [])
                context.user_data[category][field] = selected

                keyboard = [
                    [InlineKeyboardButton(x + ' ✅' * (x in selected), callback_data=x)]
                    for x in CHECKBOX[field]
                ]
                if field == 'bedrooms':
                    keyboard = [
                        [k[0] for k in keyboard[:5]],
                        [k[0] for k in keyboard[5:]],
                    ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                msg_obj = await update.message.reply_text(
                    'Please choose:', reply_markup=reply_markup
                )
            elif field == 'excluded_words':
                msg_obj = await update.message.reply_text(EXCLUDED_WORDS_TEXT)
            context.user_data['last_action'] = field
            context.user_data['msg_obj'] = msg_obj
            return

        if 'min' in last_action or 'max' in last_action or last_action == 'radius':
            if not msg.isnumeric():
                return await update.message.reply_text(
                    f'Value for {last_action} should be string.'
                )
            context.user_data[category][last_action] = int(msg)
            context.user_data['last_action'] = 'choose_category'
            await context.bot.edit_message_text(
                text=f'Selected value for {last_action}: {msg}',
                message_id=context.user_data['msg_obj'].message_id,
                chat_id=update.effective_chat.id,
            )
        elif last_action == 'excluded_words':
            context.user_data[category][last_action] = msg
            context.user_data['last_action'] = 'choose_category'
            await context.bot.edit_message_text(
                text=f'Selected {last_action} are: {msg}',
                message_id=context.user_data['msg_obj'].message_id,
                chat_id=update.effective_chat.id,
            )
        else:
            return await update.message.reply_text(
                'Unknown action. Try again or choose other property'
            )

    async def handle_choose(self, update: Update, context: DEFAULT_TYPE, msg: str):
        category = msg.split()[0]
        if not category in TG_CATEGORIES:
            return await self.start(
                update, context, 'Unknown command. Please start again'
            )
        context.user_data['category'] = category
        context.user_data['last_action'] = 'choose_category'
        context.user_data.setdefault(category, {})
        await update.message.reply_text(
            text=CHOOSE_CATEGORY_TEXT,
            reply_markup=ReplyKeyboardMarkup(TG_CATEGORIES[category]['buttons']),
        )

    async def handle_save(self, update: Update, context: DEFAULT_TYPE):
        category = context.user_data['category']
        props = context.user_data[category]
        await self.update_checkbox(update, context)
        txt_props = '\n'.join(f'{k}: {v}' for k, v in props.items() if k and k != 'id' and k != 'saved')
        text = f'{SAVE_PREFIX}\n{txt_props}' if txt_props else ''
        reply_markup = None
        if 'city' in props and 'radius' in props:
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(SAVE, callback_data=SAVE)]]
            )
        else:
            text += ('\n\n' * bool(text)) + 'Describe city/radius to save parameters.'
        msg_obj = await update.message.reply_text(text, reply_markup=reply_markup)
        context.user_data['last_action'] = SAVE
        context.user_data['msg_obj'] = msg_obj

    async def update_checkbox(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        category = context.user_data['category']
        last_action = context.user_data['last_action']
        if last_action in CHECKBOX:
            selected = ', '.join(context.user_data[category][last_action])
            await context.bot.edit_message_text(
                text=f'Selected {last_action} are: {selected}',
                message_id=context.user_data['msg_obj'].message_id,
                chat_id=update.effective_chat.id,
            )
        elif last_action == SAVE:
            msg_obj = context.user_data['msg_obj']
            await context.bot.edit_message_text(
                text='Continue editing...' + msg_obj.text[len(SAVE_PREFIX) :],
                message_id=msg_obj.message_id,
                chat_id=update.effective_chat.id,
            )

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        category = context.user_data.get('category')
        last_action = context.user_data.get('last_action')

        await query.answer()

        if not (last_action and category):
            await query.edit_message_text('No selection')
            return await self.start(
                update, context, 'Unknown last_action. Please start again'
            )

        if last_action == SAVE:
            user_id = update.effective_user.id
            await query.edit_message_text(
                'Saved:' + query.message.text[len(SAVE_PREFIX) :]
            )
            context.user_data['last_action'] = None
            context.user_data[category]['saved'] = True
            self.storage.save_user_ad_params(user_id, category, context.user_data[category])
            if not context.user_data.get('user_exists'):
                self.storage.save_user(user_id)
            return await self.start(update, context, 'Search params were saved.')

        keyboard = query.message.reply_markup.inline_keyboard
        for i, keys in enumerate(keyboard):
            for j, key in enumerate(keys):
                if query.data != key['callback_data']:
                    continue
                if '✅' in key['text']:
                    t = key['text'][:-2]
                    context.user_data[category][last_action].remove(query.data)
                else:
                    t = key['text'] + ' ✅'
                    context.user_data[category][last_action].append(query.data)
                keyboard[i][j] = InlineKeyboardButton(t, callback_data=query.data)
                break
            else:
                continue
            break
        else:
            return await update.message.reply_text('Unknown error. Try again.')
        await query.edit_message_text(
            query.message.text, reply_markup=query.message.reply_markup
        )


if __name__ == '__main__':
    tg_updater = TgUpdater()
    tg_updater.run()


"""
Просмотр, что уже выбрано по текущей категории
Кнопочка старт серч, стоп серч в зависимости от того,
есть ли что искать; и запущен ли поиск

Сделать проверку юзеров, которые старше месяца останавливать поиск и предупреждать их об этом

Сделать возможность просмотра уже существующих сэйвов

Не давать пользователю создавать еще поиск по тому же городу
"""

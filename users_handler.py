from datetime import datetime
from typing import Any, Dict, List

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
from storage import Storage
from utils import init_logger

CTX = ContextTypes.DEFAULT_TYPE
SAVE_PREFIX = 'Current parameters are:'

BEFORE_START_TEXT = '''
Hello! I can find new ads about rent house/flat or buying car/motorbike on Cyprus.
For start searching, press Start and put cryterias.
'''
CHOOSE_CATEGORY_TEXT = (
    'You should choose at least any city and the radius to start polling ads.'
)
MAIN_SCREEN_TEXT = 'Choose category to set up searching parameters'
SWW_TEXT = 'Something went wrong. Try to choose category again'
UNKNOWN_CMD = 'Unknown command. Try again, or type /start to reload bot'
SELECTED_SIGN = '✅'
TEXTS = {
    'run': 'run searching 🟢',
    'stop': 'stop searching ⛔️',
    'history': 'current search parameters 📒',
    'save': 'save',
    'delete': 'delete',
    'back': 'back to menu',
    'choose': 'choose',
    'prefix_choose_int': 'Please type value for ',
    'excluded_words_text': 'Please input comma separted words. If any of them are in title, ad will be ignored.',
    'settings': 'settings 🔧',
}
KB = {
    'run': KeyboardButton(TEXTS['run']),
    'stop': KeyboardButton(TEXTS['stop']),
    'history': KeyboardButton(TEXTS['history']),
    'settings': KeyboardButton(TEXTS['settings']),
}
IKM = {
    'save': InlineKeyboardMarkup(
        [[InlineKeyboardButton(TEXTS['save'], callback_data=TEXTS['save'])]]
    ),
    'delete': InlineKeyboardMarkup(
        [[InlineKeyboardButton(TEXTS['delete'], callback_data=TEXTS['delete'])]]
    ),
}


def generate_buttons(btns_text) -> List[List[KeyboardButton]]:
    return [
        [KeyboardButton(f'{TEXTS["choose"]} {t}') for t in g]
        for g in [['cities', 'radius'], ['price_min', 'price_max']] + btns_text
    ] + [[KeyboardButton(TEXTS['save']), KeyboardButton(TEXTS['back'])]]


TG_CATEGORIES = {
    CATEGORY_RENT: {
        'text': f'{CATEGORY_RENT} 🏘',
        'main_btn': KeyboardButton(f'{CATEGORY_RENT} 🏘'),
        'buttons': generate_buttons(
            [
                ['area_min', 'area_max'],
                ['bedrooms', 'furnishing'],
                ['pets', 'excluded_words'],
            ]
        ),
    },
    CATEGORY_MOTORBIKES: {
        'text': f'{CATEGORY_MOTORBIKES} 🏍',
        'main_btn': KeyboardButton(f'{CATEGORY_MOTORBIKES} 🏍'),
        'buttons': generate_buttons(
            [['mileage_min', 'mileage_max'], ['types', 'excluded_words']]
        ),
    },
    CATEGORY_CARS: {
        'text': f'{CATEGORY_CARS} 🚗',
        'main_btn': KeyboardButton(f'{CATEGORY_CARS} 🚗'),
        'buttons': generate_buttons(
            [
                ['mileage_min', 'mileage_max'],
                ['year_min', 'year_max'],
                ['gearbox', 'excluded_words'],
            ]
        ),
    },
}


class TgUpdater:
    def __init__(self) -> None:
        self.application = ApplicationBuilder().token(TOKEN).build()
        self.application.add_handler(CommandHandler('start', self.handle_cmd_start))
        self.application.add_handler(CallbackQueryHandler(self.handle_btn))
        self.application.add_handler(MessageHandler(filters.TEXT, self.handle_text))

        self.storage = Storage()

    def run(self) -> None:
        self.application.run_polling()

    async def handle_cmd_start(self, update: Update, context: CTX):
        await self.load_user_data(update, context)
        await self.handle_last_message(context)
        await self.show_main_screen(update, context)

    async def handle_btn(self, update: Update, context: CTX):
        await self.load_user_data(update, context)
        query = update.callback_query
        await query.answer()
        if query.data.startswith('checkbox_'):
            return await self.handle_btn_checkbox(update, context)
        elif query.data == TEXTS['delete']:
            await self.handle_btn_delete(update, context)
            context.user_data['last_message'] = None
        elif query.data == TEXTS['save']:
            await self.handle_btn_save(update, context)
            context.user_data['last_message'] = None
        elif query.data.startswith('settings_'):
            await self.handle_btn_settings(update, context)
        else:
            await query.edit_message_text('Unknown action')
            await self.show_main_screen(update, context, SWW_TEXT)
            context.user_data['last_message'] = None

    async def handle_btn_checkbox(self, update: Update, context: CTX):
        query = update.callback_query
        if not (category := context.user_data.get('category')):
            await query.edit_message_text('Session expired. Retry')
            return await self.show_main_screen(update, context, SWW_TEXT)
        keyboard = query.message.reply_markup.inline_keyboard
        _, field, value = query.data.split('_')
        for i, keys in enumerate(keyboard):
            for j, key in enumerate(keys):
                if query.data != key['callback_data']:
                    continue
                if SELECTED_SIGN in key['text']:
                    text = key['text'][:-2]
                    context.user_data[category][field].remove(value)
                else:
                    text = key['text'] + f' {SELECTED_SIGN}'
                    context.user_data[category][field].append(value)
                keyboard[i][j] = InlineKeyboardButton(text, callback_data=query.data)
                break
            else:
                continue
            break
        else:
            return await update.message.reply_text(UNKNOWN_CMD)
        await query.edit_message_text(
            query.message.text, reply_markup=query.message.reply_markup
        )

    async def handle_btn_delete(self, update: Update, context: CTX):
        query = update.callback_query
        category = query.message.text.split()[0]
        user_id = update.effective_user.id

        self.storage.delete_user_params_by_category(user_id, category)
        if category in context.user_data:
            del context.user_data[category]
        await query.edit_message_text(
            query.message.text.replace('are', 'have been removed')
        )

    async def handle_btn_save(self, update: Update, context: CTX):
        query = update.callback_query
        if not (category := context.user_data.get('category')):
            await query.edit_message_text('Session expired. Retry')
            return await self.show_main_screen(update, context, SWW_TEXT)
        user_id = update.effective_user.id
        if self.missed_fields_for_save(context.user_data[category]):
            return await query.edit_message_text(
                query.message.text.replace(
                    SAVE_PREFIX,
                    'Not saved, as {missed_text} are not specified. Specified options:',
                )
            )

        await query.edit_message_text(query.message.text.replace(SAVE_PREFIX, 'Saved:'))
        context.user_data[category]['saved'] = True
        self.storage.upsert_user_ad_params(
            user_id, category, context.user_data[category]
        )
        if not context.user_data['settings']:
            context.user_data['settings']['active'] = False
            self.storage.upsert_user_settings(
                user_id, created_at=datetime.utcnow(), active=False
            )
        await self.show_main_screen(update, context, 'You can set up another search')

    async def handle_btn_settings(self, update: Update, context: CTX):
        query = update.callback_query
        keyboard = query.message.reply_markup.inline_keyboard
        _, field = query.data.split('_', maxsplit=1)
        for i, keys in enumerate(keyboard):
            if query.data != keys[0]['callback_data']:
                continue
            if SELECTED_SIGN in keys[0]['text']:
                text = keys[0]['text'][:-2]
                context.user_data['settings'][field] = False
            else:
                text = keys[0]['text'] + f' {SELECTED_SIGN}'
                context.user_data['settings'][field] = True
            keyboard[i] = [InlineKeyboardButton(text, callback_data=query.data)]
            break
        else:
            return await update.message.reply_text(UNKNOWN_CMD)
        await query.edit_message_text(
            query.message.text, reply_markup=query.message.reply_markup
        )
        self.storage.upsert_user_settings(
            update.effective_user.id, **context.user_data['settings']
        )

    async def handle_text(self, update: Update, context: CTX):
        await self.load_user_data(update, context)
        await self.handle_last_message(context)
        message_text = update.effective_message.text
        category = context.user_data.get('category')

        if message_text == TEXTS['back']:
            return await self.show_main_screen(update, context)

        if message_text in (TEXTS['run'], TEXTS['stop']):
            return await self.handle_text_searching_status(update, context)

        if message_text == TEXTS['history']:
            return await self.handle_text_history(update, context)

        if message_text == TEXTS['settings']:
            return await self.handle_text_settings(update, context)

        if message_text in (c['text'] for c in TG_CATEGORIES.values()):
            return await self.show_category_screen(update, context)

        if not category:
            return await self.show_main_screen(
                update, context, 'Session expired. Choose category again'
            )

        if message_text == TEXTS['save']:
            return await self.handle_text_save(update, context)

        if message_text.startswith(TEXTS["choose"]):
            return await self.handle_text_choose(update, context)

        if context.user_data.get('last_message'):
            return await self.handle_text_last_action(update, context)

        return await update.message.reply_text(
            'Unknown action. Try again or choose other property'
        )

    async def handle_text_searching_status(self, update: Update, context: CTX):
        active = update.effective_message.text == TEXTS['run']
        context.user_data['settings']['active'] = active
        self.storage.upsert_user_settings(update.effective_user.id, active=active)
        await self.show_main_screen(
            update, context, 'Searching ' + ('started' if active else 'stopped')
        )

    async def handle_text_history(self, update: Update, context: CTX):
        text = ''
        for tg_category in TG_CATEGORIES:
            if 'saved' in context.user_data.get(tg_category, {}):
                txt_props = '\n'.join(
                    f'{k}: {v}'
                    for k, v in context.user_data[tg_category].items()
                    if v and k != 'saved' and k != 'id'
                )
                text = f'{tg_category} parameters are:\n{txt_props}'
                await update.message.reply_text(text, reply_markup=IKM['delete'])
        if not text:
            await update.message.reply_text('No saved searching paremeters yet')

    async def handle_text_settings(self, update: Update, context: CTX):
        settings = context.user_data['settings']
        keyboard = [
            [
                InlineKeyboardButton(
                    f'{x}' + SELECTED_SIGN * (settings.get(x) or False),
                    callback_data=f'settings_{x}',
                )
            ]
            for x in USER_FIELDS_TO_SHOW
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await update.message.reply_text(
            f'Please choose:', reply_markup=reply_markup
        )
        context.user_data['last_message'] = (TEXTS['settings'], message)

    async def handle_text_last_action(self, update: Update, context: CTX):
        last_message = context.user_data['last_message'][1]
        message_text = update.effective_message.text
        category = context.user_data['category']
        if last_message.text.startswith(TEXTS['prefix_choose_int']):
            field = last_message.text[len(TEXTS['prefix_choose_int']) :]
            if not message_text.isnumeric() or int(message_text) < 0:
                return await update.message.reply_text(
                    f'Value for {field} should be not negative int.'
                )
            context.user_data[category][field] = int(message_text)
            await last_message.edit_text(
                text=f'Selected value for {field}: {message_text}',
            )
            context.user_data['last_message'] = None
        elif last_message.text == TEXTS['excluded_words_text']:
            context.user_data[category]['excluded_words'] = message_text
            await last_message.edit_text(
                text=f'Selected excluded words are: {message_text}',
            )
            context.user_data['last_message'] = None

    async def handle_text_save(self, update: Update, context: CTX):
        category = context.user_data['category']
        props = context.user_data[category]
        props_text = self.form_props_text(props)
        text = f'{SAVE_PREFIX}\n{props_text}' if props_text else ''
        reply_markup = None
        if missed_fields_for_save := self.missed_fields_for_save(props):
            text += ('\n\n' * bool(text)) + 'Describe {} to save parameters.'.format(
                ', '.join(missed_fields_for_save)
            )
        else:
            reply_markup = IKM['save']
        last_message = await update.message.reply_text(text, reply_markup=reply_markup)
        context.user_data['last_message'] = (TEXTS['save'], last_message)

    async def handle_text_choose(self, update: Update, context: CTX):
        message_text = update.effective_message.text
        category = context.user_data['category']
        field = message_text.split(maxsplit=1)[-1]
        if 'min' in field or 'max' in field or field == 'radius':
            message = await update.message.reply_text(
                TEXTS['prefix_choose_int'] + field
            )
        elif field in CHECKBOX:
            selected = context.user_data[category].setdefault(field, [])
            keyboard = [
                [
                    InlineKeyboardButton(
                        f'{x}' + SELECTED_SIGN * (x in selected),
                        callback_data=f'checkbox_{field}_{x}',
                    )
                ]
                for x in CHECKBOX[field]
            ]
            if field == 'bedrooms':
                keyboard = [
                    [k[0] for k in keyboard[:5]],
                    [k[0] for k in keyboard[5:]],
                ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await update.message.reply_text(
                f'Please choose:', reply_markup=reply_markup
            )
        elif field == 'excluded_words':
            message = await update.message.reply_text(TEXTS['excluded_words_text'])
        else:
            return await update.message.reply_text(SWW_TEXT)
        context.user_data['last_message'] = (field, message)

    async def show_main_screen(
        self, update: Update, context: CTX, text: str = MAIN_SCREEN_TEXT
    ):
        buttons = [[x['main_btn']] for x in TG_CATEGORIES.values()] + [[KB['settings']]]

        if status := context.user_data['settings']:
            buttons.append([KB['history']])
            buttons.append([KB['stop'] if status else KB['run']])

        markup = ReplyKeyboardMarkup(buttons)
        await update.effective_chat.send_message(text, reply_markup=markup)

    async def show_category_screen(self, update: Update, context: CTX):
        category = update.effective_message.text.split()[0]
        context.user_data['category'] = category
        context.user_data.setdefault(category, {})
        await update.message.reply_text(
            text=CHOOSE_CATEGORY_TEXT,
            reply_markup=ReplyKeyboardMarkup(TG_CATEGORIES[category]['buttons']),
        )

    async def load_user_data(self, update: Update, context: CTX):
        if context.user_data:
            return
        user_id = update.effective_user.id
        if (settings := self.storage.get_users_settings(user_id)) is None:
            context.user_data['settings'] = {}
        else:
            context.user_data['settings'] = settings
            for (category, users) in self.storage.get_users_ad_params(user_id).items():
                for _, props in users.items():
                    context.user_data[category] = {
                        **{k: v for k, v in props.items() if v},
                        'saved': True,
                    }

    async def handle_last_message(self, context: CTX):
        if not (last_message := context.user_data.get('last_message')):
            return
        field, message = last_message
        if field == TEXTS['save']:
            await message.edit_text(
                message.text.replace(SAVE_PREFIX, 'Continue editing...')
            )
        elif field in CHECKBOX:
            category = context.user_data['category']
            selected = ', '.join(context.user_data[category].get(field))
            await message.edit_text(text=f'Selected {field} are: {selected}')
        elif field == TEXTS['settings']:
            selected = ','.join(
                k
                for k, v in context.user_data['settings'].items()
                if k in USER_FIELDS_TO_SHOW and v
            )
            await message.edit_text(text=f'Selected settings are: {selected}')
        else:
            return
        context.user_data['last_message'] = None

    def form_props_text(self, props: Dict[str, Any]) -> str:
        return '\n'.join(
            f'{k}: {v}' for k, v in props.items() if v and k != 'id' and k != 'saved'
        )

    def missed_fields_for_save(
        self, user_data_by_category: Dict[str, Any]
    ) -> List[str]:
        return [f for f in ('cities', 'radius') if f not in user_data_by_category]


if __name__ == '__main__':
    init_logger()
    tg_updater = TgUpdater()
    tg_updater.run()

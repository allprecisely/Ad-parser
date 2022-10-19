C = category
UD - user_data
UDC = category in UD

Параметры в UD:
active - активирован ли поиск?
category - текущая категория
rent/cars/motorbikes - дикты с параметрами

MS(текст='Choose category to set up searching parameters') - main screen:
1) Формируется сообщение с переданным текстом
- текст - всегда передается
- добавляются 3 кнопки с категориями в сообщении

2) Проверяем кэш
2.1) кэш есть -> (3)
2.2) кэша нет -> идем в базу за юзером
2.2.3) юзера нет -> (3)
2.2.4) юзер есть -> идем в базу за критериями поиска по юзеру
2.2.4.1) критериев нет -> если юзер актив, то в базе юзера деактивируем -> (3)
2.2.4.2) критерии есть -> сохраняем критерии в кэш, добавляя метку saved внутрь дикта для каждой категории; соответсвующий актив в кэш

3) проверяем актив в кэше
3.1) актива нет -> (4)
3.2) актив есть -> добавляем в (1) 2 кнопки с историей и статусом актива

4) отрисовываем сообщение с кнопками

CS() - category screen:
1) Проверяем кэш
1.1) если в кэше нет категории


/start
MS()

btns
1) Проверяем категорию в кэше
1.1) категории нет -> правим msg_obj на Sesstion expired; MS('Something went wrong. Try to choose category again') -> R
category = cache.category

Если data == 'save'
Если параметры категории в кэше не содержат cities и radius -> форматим query в Not saved: <ad_params>; CS('Describe <> to be able to save search parameters') -> R
Сохраняем параметры из кэша по категории в базе; добавляем сейвд в кэш; форматируем query в Saved: <ad_params>; MS() -> R

Если data startswith checkbox_
key, value = data[len(checkbox_):].split()
if key not in CATEGORIES_SETTINGS[category]



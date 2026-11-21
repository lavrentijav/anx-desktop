"""All user-visible strings live here (Russian is the default locale).

The wording follows the 11 BETA 2 logic handoff.  Widgets must not contain
display literals -- use this module so texts stay consistent and translatable.
"""

from __future__ import annotations


class S:
    APP_NAME = "anx-desktop"
    APP_VERSION = "0.1.0 · clean-room UI"

    # ------------------------------------------------------------- navigation
    NAV_HOME = "Главная"
    NAV_DISCOVER = "Обзор"
    NAV_BOOKMARKS = "Закладки"
    NAV_FEED = "Лента"
    NAV_SEARCH = "Поиск"
    NAV_PROFILE = "Профиль"
    NAV_SETTINGS = "Настройки"
    NAV_CHANNELS = "Каналы"
    NAV_ARTICLES = "Записи"
    NAV_COLLECTIONS = "Коллекции"
    NAV_HISTORY = "История"
    NAV_NOTIFICATIONS = "Уведомления"
    NAV_BADGES = "Значки"
    NAV_HEALTH = "Здоровье аккаунта"
    NAV_DELETION = "Удаление аккаунта"
    NAV_AUTH = "Авторизация"
    NAV_NEED_AUTH = "Требуется вход"
    NAV_MAIN_GROUP = "Основное"
    NAV_LIBRARY_GROUP = "Библиотека"
    NAV_ACCOUNT_GROUP = "Аккаунт"
    NAV_COLLAPSE = "Свернуть меню"
    NAV_EXPAND = "Развернуть меню"

    # ----------------------------------------------------------------- common
    BACK = "Назад"
    FORWARD = "Вперёд"
    REFRESH = "Обновить"
    SETTINGS = "Настройки"
    NOTIFICATIONS = "Уведомления"
    PROFILE = "Профиль"
    SEARCH = "Поиск"
    FILTER = "Фильтр"
    APPLY = "Применить"
    RESET = "Сбросить"
    RETRY = "Повторить"
    HELP = "Помощь"
    CLOSE = "Закрыть"
    CANCEL = "Отмена"
    DELETE = "Удалить"
    SAVE = "Сохранить"
    SEND = "Отправить"
    SHARE = "Поделиться"
    COPY_LINK = "Скопировать ссылку"
    REPORT = "Пожаловаться"
    CREATE = "Создать"
    MORE = "Ещё"
    ALL = "Все"
    LOADING = "Загрузка…"
    SHOW_MORE = "Показать ещё"
    SHOW_ALL = "Показать все"
    SELECT = "Выбрать"
    DONE = "Готово"
    OK = "Понятно"
    ON = "Вкл."
    OFF = "Выкл."
    ENABLED = "Включено"
    DISABLED = "Отключено"
    YES = "Да"
    NO = "Нет"
    TODAY = "Сегодня"
    YESTERDAY = "Вчера"
    NOT_SET = "Не задано"
    NEW = "Новое"
    PINNED = "Закреплено"
    PRIVATE = "Приватная"
    DELETED = "Удалено"
    VERIFIED = "Подтверждён"
    SPONSOR = "Спонсор"
    ONLINE = "В сети"
    OFFLINE = "Не в сети"
    DEMO = "Демо"
    DEMO_DATA = "Данные"
    DEMO_EMPTY = "Пусто"
    DEMO_ERROR = "Ошибка"

    # ------------------------------------------------------------ state texts
    ERROR_TITLE = "Ой, что-то не так…"
    ERROR_TEXT = "Произошла ошибка при загрузке"
    ERROR_OFFLINE = "Нет подключения к сети. Проверьте соединение и повторите попытку."
    EMPTY_TITLE = "Ой, а тут ничего нет!"
    EMPTY_HINT = "Попробуйте изменить запрос или загляните позже."
    EMPTY_SEARCH_TITLE = "Ой, ничего не нашлось!"
    EMPTY_SEARCH_HINT = "Попробуйте другой запрос или снимите часть фильтров."
    EMPTY_NOTIFICATIONS = "Нет уведомлений"
    EMPTY_COMMENTS = "Еще никто не оставлял комментарии. Будьте первыми!"
    EMPTY_CHANNELS = "Похоже, нет ни одного канала"
    EMPTY_ARTICLES = "Похоже, нет ни одной записи"
    EMPTY_BADGES = "Значков пока нет :("
    EMPTY_BADGES_HINT = (
        "Вы можете получить значки за определенные действия, участие в событиях и конкурсах"
    )
    EMPTY_RELEASE_BADGES = "Нет значков"
    EMPTY_RELEASE_BADGES_HINT = "Для этого релиза пока нет значков"
    EMPTY_COLLECTION = "В коллекции пока нет релизов"
    NEED_AUTH_TITLE = "Еще не с нами?!"
    NEED_AUTH_TEXT = "Войдите или создайте профиль, чтобы открыть этот раздел."
    NEED_AUTH_ACTION = "Авторизация"
    LOADING_DATA = "Загружаем данные…"
    LOADING_DETAILS = "Загружаем подробности…"
    NOT_FOUND = "Ничего не найдено"
    PRIVATE_COLLECTION_TITLE = "Коллекция недоступна"
    PRIVATE_COLLECTION_TEXT = (
        "Данная коллекция недоступна для просмотра, поскольку автор сделал её приватной."
    )
    DELETED_COLLECTION_TEXT = "Данная коллекция была удалена и больше недоступна для просмотра."
    DELETED_PROFILE = "Профиль удалён"
    BANNED_PROFILE = "Профиль заблокирован"
    INSUFFICIENT_VOTES = "Недостаточно голосов для отображения рейтинга"
    ADULT_WARNING = "Материал содержит откровенный контент и доступен только взрослым."
    DELETE_ALL_TITLE = "Очистить все уведомления?"
    DELETE_ALL_TEXT = "Действие нельзя отменить."
    HISTORY_CLEAR_TITLE = "Очистить историю просмотра?"
    HISTORY_CLEAR_TEXT = "Отметки о просмотре сохранятся, но история будет пуста."
    REPORT_TITLE = "Пожаловаться"
    REPORT_REASON = "Причина"
    REPORT_MESSAGE = "Сообщение"
    REPORT_REASONS = ("Спам", "Оскорбления", "Спойлеры", "Нарушение правил", "Другое")
    REPORT_SENT = "Жалоба отправлена"
    COPIED = "Скопировано в буфер обмена"
    CACHE_CLEARED = "Кэш очищен"
    LINK_COPIED = "Ссылка скопирована"
    NOTIFICATION_DELETED = "Уведомление удалено"
    MOVED_TO_FAVORITES = "Добавлено в избранное"
    REMOVED_FROM_FAVORITES = "Удалено из избранного"
    SUBSCRIBED = "Вы подписались на канал"
    UNSUBSCRIBED = "Вы отписались от канала"
    SET_DEFAULT_TAB = "Вкладка назначена по умолчанию"
    FILTER_APPLIED = "Параметры применены"
    FILTER_SET_TO_MY_TAB = "Параметры применены к «Моя вкладка»"
    PLAYER_STUB = "Бэкенд воспроизведения ещё не подключён"
    PLAYER_DEFAULT_EPISODE = "Серия 1"
    PLAYER_DEFAULT_RELEASE = "Релиз"
    RATING_ACCESSIBLE_NAME = "Оценка"
    SWITCH_ACCESSIBLE_NAME = "Переключатель"

    # ------------------------------------------------------------------- tabs
    HOME_TABS = (
        "Моя вкладка",
        "Аниме",
        "Дунхуа",
        "Последнее",
        "Онгоинги",
        "Анонсы",
        "Завершенные",
        "Фильмы",
        "OVA",
    )
    HOME_TAB_SUBTITLES = (
        "Персонально настроенный раздел",
        "Японская анимация",
        "Китайская анимация",
        "Последние обновления",
        "Выходящие релизы",
        "Будущие релизы",
        "Завершённые релизы",
        "Полнометражные фильмы",
        "OVA-выпуски",
    )
    BOOKMARK_TABS = (
        "Коллекции",
        "История",
        "Избранное",
        "Смотрю",
        "В планах",
        "Просмотрено",
        "Отложено",
        "Брошено",
    )
    FEED_TABS = ("Моя лента", "Свежее", "Управляемые")
    NOTIFICATION_FILTERS = (
        "Все уведомления",
        "Только эпизоды",
        "Только релизы",
        "Только записи",
        "Только дружба",
        "Только ответы",
    )
    PROFILE_SECTIONS = (
        "Статистика",
        "Оценки релизов",
        "Коллекции",
        "Комментарии",
        "Видео",
        "Значки",
    )
    HEALTH_TABS = ("Аккаунт", "Контент")

    # ------------------------------------------------------------------- home
    HOME_VIEW_LIST = "Списком"
    HOME_VIEW_GRID = "Карточками"
    HOME_COUNT = "{count} ВСЕГО"
    HOME_DEFAULT_TAB = "Назначить по умолчанию"
    HOME_TAB_SETTINGS = "Настройки вкладки"
    HOME_EDIT_TAB = "Настроить мою вкладку"
    HOME_NEW_ARTICLES = "Новые записи"
    HOME_CONTINUE = "Продолжить просмотр"
    HOME_CONTINUE_EPISODE = "Серия {episode} · {title}"
    HOME_CONTINUE_HIDE = "Скрыть «Продолжить просмотр»"

    # --------------------------------------------------------------- discover
    DISCOVER_TRENDING = "Актуальное"
    DISCOVER_RECOMMENDATIONS = "Рекомендации"
    DISCOVER_RECOMMENDATIONS_HINT = "Популярные и актуальные"
    DISCOVER_BASED_ON_VOTES = "На основе ваших оценок"
    DISCOVER_DISCUSSED = "Обсуждаемое сегодня"
    DISCOVER_SOCIAL = "Мы в соцсетях"
    DISCOVER_WATCHING_NOW = "Смотрят сейчас"
    DISCOVER_COLLECTIONS_WEEK = "Коллекции недели"
    DISCOVER_COMMENTS_WEEK = "Комментарии недели"
    DISCOVER_SPONSORSHIP = "Поддержать проект"
    DISCOVER_SPONSORSHIP_TEXT = "Проект живёт благодаря добровольной поддержке."
    DISCOVER_SPONSORSHIP_ACTION = "Узнать подробнее"
    DISCOVER_EMPTY_RECOMMENDATIONS = (
        "Продолжайте смотреть и оценивать аниме — здесь появятся рекомендации."
    )
    DISCOVER_QUICK_NEW = "Новинки"
    DISCOVER_QUICK_SCHEDULE = "Расписание"
    DISCOVER_QUICK_UPDATES = "Обновления серий"
    DISCOVER_QUICK_COLLECTIONS = "Коллекции"
    DISCOVER_QUICK_FILTER = "Фильтр"

    # ------------------------------------------------------------------ feed
    FEED_CREATE_ARTICLE = "Создать запись"
    FEED_CREATE_CHANNEL = "Создать канал"
    FEED_EMPTY_TITLE = "Ой, а подписок-то нет!"
    FEED_EMPTY_TEXT = (
        "Но ничего страшного, Вы можете подписаться на популярные каналы из списка ниже"
    )
    FEED_READY_TITLE = "Отлично, почти готово!"
    FEED_READY_TEXT = (
        "Вы подписались на необходимое количество каналов. Может, найдёте для себя ещё что-то интересное?"
    )
    FEED_SUBSCRIBE = "Подписаться"
    FEED_UNSUBSCRIBE = "Отписаться"
    FEED_MUTE = "Скрыть канал"
    FEED_UNMUTE = "Отменить скрытие канала"
    FEED_COMMENTS = "Комментарии"
    FEED_REACTIONS = "Реакции"
    FEED_REPOSTS = "Репосты"
    FEED_TAGS = "Теги"

    # ---------------------------------------------------------------- search
    SEARCH_PLACEHOLDER = "Поиск аниме…"
    SEARCH_USERS_PLACEHOLDER = "Поиск пользователей"
    SEARCH_HISTORY = "История поиска"
    SEARCH_CLEAR_HISTORY = "Очистить все"
    SEARCH_RESULTS = "Результаты поиска"
    SEARCH_RELEASES = "Релизы"
    SEARCH_ARTICLES = "Записи"
    SEARCH_CHANNELS = "Каналы"
    SEARCH_PROFILES = "Пользователи"
    SEARCH_COLLECTIONS = "Коллекции"
    SEARCH_OTHER = "Другие результаты"
    SEARCH_GLOBAL = "Искать в глобальном поиске"
    SEARCH_GLOBAL_STUB = "Глобальный поиск будет подключён отдельным слоем."
    SEARCH_RELATED = "Похожий запрос"
    SEARCH_RELATED_ACTION = "Перейти"
    SEARCH_VOICE = "Голосовой поиск"
    SEARCH_VOICE_STUB = "Голосовой поиск появится позже"
    SEARCH_STALE = "Результаты устарели"

    # ---------------------------------------------------------------- filter
    FILTER_TITLE = "Фильтр"
    FILTER_SUBTITLE = "Настройте подборку релизов"
    FILTER_COUNTRY = "Страна"
    FILTER_CATEGORY = "Категория"
    FILTER_GENRES = "Жанры"
    FILTER_GENRES_MODE = "Режим жанров"
    FILTER_GENRES_ALL = "Все"
    FILTER_GENRES_ANY = "Любой"
    FILTER_GENRES_EXCLUDE = "Исключить"
    FILTER_GENRES_ALL_HINT = "Покажем релизы со всеми выбранными жанрами."
    FILTER_GENRES_ANY_HINT = "Покажем релизы хотя бы с одним выбранным жанром."
    FILTER_GENRES_EXCLUDE_HINT = "Покажем только релизы без выбранных жанров."
    FILTER_GENRES_WARNING = "Выбрано слишком много жанров — результат может быть пустым."
    FILTER_EXCLUDE_BOOKMARKS = "Исключить закладки"
    FILTER_TYPES = "Озвучки"
    FILTER_STUDIO = "Студия"
    FILTER_SOURCE = "Первоисточник"
    FILTER_YEARS = "Годы"
    FILTER_SEASON = "Сезон"
    FILTER_EPISODES = "Эпизоды"
    FILTER_STATUS = "Статус"
    FILTER_DURATION = "Длительность эпизода"
    FILTER_AGE = "Возрастное ограничение"
    FILTER_SORT = "Сортировка"
    FILTER_COPY_LINK = "Скопировать ссылку на фильтр"
    FILTER_SET_MY_TAB = "Установить для «Моя вкладка»"
    FILTER_RESULTS = "Результаты фильтра"
    FILTER_CHANGE = "Изменить"
    FILTER_ANY = "Любой"
    FILTER_YEAR_RANGE = "2000–2026"
    FILTER_COUNTRIES = ("Любая", "Япония", "Китай", "Корея")
    FILTER_CATEGORIES = ("Любая", "ТВ-сериал", "Фильм", "OVA", "ONA")
    FILTER_TYPE_OPTIONS = ("Любые", "Озвучка", "Субтитры")
    FILTER_STUDIOS = ("Любая", "Studio Demo", "North Light", "Paper Plane")
    FILTER_SOURCES = ("Любой", "Манга", "Ранобэ", "Оригинал", "Игра")
    FILTER_YEAR_OPTIONS = (FILTER_YEAR_RANGE, "2026", "2025", "2024", "2020–2023")
    FILTER_SEASONS = ("Любой", "Зима", "Весна", "Лето", "Осень")
    FILTER_EPISODE_OPTIONS = ("Любые", "1–12", "13–24", "25–48", "49+")
    FILTER_STATUS_OPTIONS = ("Любой", "Выходит", "Завершён", "Анонс")
    FILTER_DURATION_OPTIONS = ("Любая", "До 15 мин.", "15–30 мин.", "30+ мин.")
    FILTER_AGE_OPTIONS = ("Любое", "0+", "6+", "12+", "16+", "18+")
    FILTER_SORT_OPTIONS = ("По популярности", "По рейтингу", "По дате", "По названию")
    FILTER_EXCLUDE_OPTIONS = (
        "Не исключать",
        "Коллекции",
        "История",
        "Избранное",
        "Смотрю",
        "В планах",
        "Просмотрено",
        "Отложено",
        "Брошено",
    )
    FILTER_GENRE_NAMES = (
        "Фэнтези", "Приключения", "Драма", "Романтика", "Повседневность",
        "Фантастика", "Детектив", "Комедия", "Школа", "Спорт", "Мистика",
        "Триллер", "Музыка", "Меха", "Историческое",
    )
    COLLECTIONS_SORT_NEW = "Недавно добавленные"
    COLLECTIONS_SORT_FAVORITES = "По избранному"
    COLLECTIONS_SORT_POPULAR = "По популярности"
    AUTHOR_PREFIX = "Автор: {author}"
    COLLECTION_RELEASES = "Релизы"

    # --------------------------------------------------------------- release
    RELEASE_ABOUT = "О релизе"
    RELEASE_SCREEN_TITLE = "Релиз"
    RELEASE_COUNTRY = "Страна"
    RELEASE_EPISODES = "Эпизоды"
    RELEASE_SCHEDULE = "Расписание"
    RELEASE_STUDIO = "Студия"
    RELEASE_SOURCE = "Первоисточник"
    RELEASE_GENRES = "Жанры"
    RELEASE_DESCRIPTION = "Описание"
    RELEASE_EXPAND = "Подробнее…"
    RELEASE_COLLAPSE = "Свернуть"
    RELEASE_RATING = "Рейтинг"
    RELEASE_RATING_VOTES = "голоса"
    RELEASE_YOUR_VOTE = "Вы проголосовали"
    RELEASE_CHANGE_VOTE = "Изменить"
    RELEASE_VOTE_PROMPT = "Оцените релиз"
    RELEASE_SCREENSHOTS = "Кадры"
    RELEASE_VIDEO = "Видео"
    RELEASE_BADGES = "Значки релиза"
    RELEASE_BADGES_HINT = "Значки этого релиза можно получить за разные действия."
    RELEASE_COLLECTIONS = "Коллекции с релизом"
    RELEASE_ADD_COLLECTION = "Добавить в коллекцию"
    RELEASE_RELATED = "Связанные релизы"
    RELEASE_RECOMMENDED = "Рекомендации"
    RELEASE_COMMENTS = "Комментарии"
    RELEASE_ALL_COMMENTS = "Все комментарии"
    RELEASE_RANDOM = "Случайный релиз"
    RELEASE_WATCH = "Смотреть"
    RELEASE_SOON = "Скоро"
    RELEASE_UNAVAILABLE = "Недоступно"
    RELEASE_UNAVAILABLE_COUNTRY = "Недоступно в вашей стране"
    RELEASE_ACTIONS = "Показать действия"
    RELEASE_ACTION_ONLINE = "Онлайн просмотр"
    RELEASE_ACTION_SHARE = "Поделиться"
    RELEASE_ACTION_COPY = "Скопировать ссылку"
    RELEASE_ACTION_HOME = "Добавить на главный экран"
    RELEASE_ACTION_REPORT = "Пожаловаться"
    RELEASE_ACTION_NOTIFICATIONS = "Уведомления по релизам"
    RELEASE_ACTION_RANDOM = "Случайный релиз"
    RELEASE_STATUS_NOT_WATCHING = "Не смотрю"
    RELEASE_FAVORITES = "Избранное"
    RELEASE_EPISODES_COUNT = "{count} эпизодов"
    RELEASE_END = "Конец экрана"
    RELEASE_END_HINT = "Вы посмотрели всё по этому релизу."

    # --------------------------------------------------------------- episodes
    EPISODES_TITLE = "Серии"
    EPISODES_ALL = "Все"
    EPISODES_VOICES = "Озвучки"
    EPISODES_SUBTITLES = "Субтитры"
    EPISODES_SORT = "Сортировка"
    EPISODES_UPDATES = "Обновления"
    EPISODES_SEARCH = "Поиск по сериям"
    EPISODES_SEASON = "{n} сезон"
    EPISODES_MARK_ALL = "Все серии просмотрены"
    EPISODES_CLEAR_MARKS = "Снять все отметки"
    EPISODES_MARK_ONE = "Снять отметку о просмотре"
    EPISODES_WATCHED_TO = "Просмотрено до {time}"
    EPISODES_FILLER = "филлер"
    EPISODES_DOWNLOAD = "Скачать"
    EPISODES_EMPTY_TITLE = "Похоже, нет ни одной серии"
    EPISODES_EMPTY_HINT = "Попробуйте выбрать другую озвучку или обновите страницу."
    EPISODES_PARTIAL_WARNING = "Часть серий не загрузилась. Попробуйте обновить."
    EPISODES_CHANNEL_WIDGET = "Виджет канала"
    EPISODES_CHANNEL_HIDE_WEEK = "Скрыть на неделю"
    EPISODES_CHANNEL_HIDE_FOREVER = "Скрыть навсегда"
    EPISODES_SOURCE_ALL = "Все озвучки"
    EPISODES_DOWNLOAD_STUB = "Загрузка серий появится позже"
    EPISODES_WATCHED = "Просмотрено"
    EPISODES_UNWATCHED = "Не просмотрено"

    # ----------------------------------------------------------------- player
    PLAYER_TITLE = "Плеер"
    PLAYER_PLAY = "Воспроизвести"
    PLAYER_PAUSE = "Пауза"
    PLAYER_PREV = "Предыдущая серия"
    PLAYER_NEXT = "Следующая серия"
    PLAYER_BACK_10 = "−10 с"
    PLAYER_FORWARD_10 = "+10 с"
    PLAYER_VOLUME = "Громкость"
    PLAYER_MUTE = "Без звука"
    PLAYER_FULLSCREEN = "Полный экран"
    PLAYER_EXIT_FULLSCREEN = "Выйти из полного экрана"
    PLAYER_PIP = "Картинка в картинке"
    PLAYER_PIP_STUB = "PiP на десктопе появится позже"
    PLAYER_LOCK = "Заблокировать контролы"
    PLAYER_UNLOCK = "Разблокировать контролы"
    PLAYER_SPEED = "Скорость"
    PLAYER_QUALITY = "Качество"
    PLAYER_SOURCE = "Озвучка"
    PLAYER_SUBTITLES = "Субтитры"
    PLAYER_SKIP_OPENING = "Перемотать"
    PLAYER_LOADING_EPISODE = "Открываем серию"
    PLAYER_LOADING_LINKS = "Получаем ссылку на видео"
    PLAYER_LOADING_CONNECTING = "Подключаемся к серверу видео"
    PLAYER_LOADING_VIDEO = "Загружаем видео"
    PLAYER_LOADING_NOT_RESPONDING = "Сервер видео не отвечает"
    PLAYER_EXIT_HINT = "Нажмите «Назад» ещё раз, чтобы выйти"
    PLAYER_BACKEND_TODO = (
        "Демонстрационный плеер. Реальный бэкенд воспроизведения будет подключён отдельно (TODO)."
    )
    PLAYER_VIDEO_UNAVAILABLE = "Видео недоступно"
    PLAYER_STREAM_FALLBACK = "Не удалось получить поток, открыт веб-плеер"
    PLAYER_CHOOSE = "Выберите плеер"
    PLAYER_ANIXPLAYER = "АниксПлеер"
    PLAYER_EMBEDDED = "Встроенный"
    PLAYER_WEB = "Веб-плеер"
    PLAYER_THIRD_PARTY = "Сторонний плеер"

    # ---------------------------------------------------------------- profile
    PROFILE_STATS = "Статистика"
    PROFILE_STATS_HELP = "Как работает статистика"
    PROFILE_STATS_HINT = "Списки, время просмотра и предпочтения"
    PROFILE_COMMENTS = "Комментарии"
    PROFILE_VIDEOS = "Видео"
    PROFILE_COLLECTIONS = "Коллекции"
    PROFILE_FRIENDS = "Друзья"
    PROFILE_WATCHED_EPISODES = "Просмотрено серий"
    PROFILE_WATCH_TIME = "Время просмотра"
    PROFILE_VOTES = "Оценки релизов"
    PROFILE_DYNAMICS = "Динамика просмотра серий"
    PROFILE_HISTORY = "История"
    PROFILE_EDIT = "Редактировать"
    PROFILE_ADD_FRIEND = "Добавить в друзья"
    PROFILE_MESSAGE = "Написать"
    PROFILE_SHARE = "Поделиться"
    PROFILE_NICK_HISTORY = "История никнейма"
    PROFILE_BLOCK = "Заблокировать"
    PROFILE_PIN_SECTION = "Закрепить секцию"
    PROFILE_SECTION_SETTINGS = "Секция профиля"
    PROFILE_THEME = "Тема витрины"
    PROFILE_INCOGNITO = "Инкогнито"
    PROFILE_REGISTERED = "На сайте с {date}"
    PROFILE_ROLE_PREFIX = "Роль"
    PROFILE_PRIVATE = "Пользователь скрыл статистику"
    PROFILE_ACHIEVEMENTS = "Значки"
    PROFILE_ACHIEVEMENTS_EDIT = "Изменить значок"
    PROFILE_BIO_EMPTY = "Статус не задан"

    # ----------------------------------------------------------------- badges
    BADGES_TITLE = "Значки"
    BADGES_SELECTED = "Закрепленные"
    BADGES_RECENT = "Недавние"
    BADGES_ALL = "Все значки"
    BADGES_OTHER = "Прочие"
    BADGES_SET = "Установить"
    BADGES_REMOVE = "Снять"
    BADGES_PIN = "Закрепить на витрине"
    BADGES_UNPIN = "Открепить"
    BADGES_REORDER = "Изменить порядок"
    BADGES_CLAIM = "Получить по коду"
    BADGES_CLAIM_HINT = "Введите код, чтобы получить значок в профиль"
    BADGES_CLAIM_ACTION = "Получить"
    BADGES_CLAIM_PLACEHOLDER = "XXXX-XXXX"
    BADGES_INFO = "О значках"
    BADGES_SHOWCASE_LIMIT = "На витрине можно закрепить не более 3 значков"
    BADGES_OWNERSHIP = "Есть у {count} пользователей"
    BADGES_HOW = "Как был получен"
    BADGES_WHY = "За что получен"
    BADGES_HIDE_UNEARNED = "Скрыть неполученные значки"
    BADGES_SHOW_UNEARNED = "Раскрыть неполученные значки"
    BADGES_RELEASE_HINT = "Значки этого релиза можно получить за разные действия."
    BADGES_RARITY_COMMON = "Обычный"
    BADGES_RARITY_UNCOMMON = "Необычный"
    BADGES_RARITY_RARE = "Редкий"
    BADGES_RARITY_EPIC = "Эпический"
    BADGES_RARITY_LEGENDARY = "Легендарный"

    # ----------------------------------------------------------------- health
    HEALTH_TITLE = "Здоровье аккаунта"
    HEALTH_SUBTITLE = "История нарушений и ограничений"
    HEALTH_OK = "Всё в порядке"
    HEALTH_LIMITED = "Есть ограничения"
    HEALTH_BLOCKED = "Аккаунт заблокирован"
    HEALTH_HISTORY = "История модерации"
    HEALTH_TAB_ACCOUNT = "Аккаунт"
    HEALTH_TAB_CONTENT = "Контент"
    HEALTH_INFO = "Как это работает"
    HEALTH_REASON = "Причина:"
    HEALTH_EMPTY = "Всё в порядке"
    HEALTH_EMPTY_HINT = "В истории нет нарушений и ограничений."
    HEALTH_APPEAL = "Подать апелляцию"
    HEALTH_DETAILS = "Технические подробности"
    HEALTH_ACTIVE = "Действует"
    HEALTH_REVOKED = "Отменена"
    HEALTH_APPEAL_SENT = "Апелляция отправлена"
    HEALTH_APPEAL_EXISTS = "Апелляция уже подана"

    # ---------------------------------------------------------------- deletion
    DELETION_TITLE = "Удаление аккаунта"
    DELETION_TEXT = (
        "Аккаунт и связанные с ним данные будут удалены без возможности восстановления "
        "после периода ожидания."
    )
    DELETION_REQUEST = "Запросить удаление аккаунта"
    DELETION_CANCEL = "Отменить запрос"
    DELETION_CONFIRM_TITLE = "Подтвердите пароль"
    DELETION_CONFIRM_TEXT = "Введите пароль, чтобы запросить удаление аккаунта."
    DELETION_BANNER = "Запрос создан"
    DELETION_DELETE_AT = "Аккаунт будет удалён {date}"
    DELETION_TIMELINE = "Как это работает"
    DELETION_STEP_1 = "Подача заявки"
    DELETION_STEP_2 = "Период ожидания"
    DELETION_STEP_3 = "Подготовка и удаление данных"
    DELETION_STEP_4 = "Аккаунт удалён"
    DELETION_STEP_1_TEXT = "Вы подтверждаете пароль и создаёте запрос."
    DELETION_STEP_2_TEXT = "В течение периода ожидания запрос можно отменить."
    DELETION_STEP_3_TEXT = "Данные аккаунта готовятся к удалению."
    DELETION_STEP_4_TEXT = "Восстановление аккаунта после этого шага невозможно."
    DELETION_TIP = "Совет"
    DELETION_TIP_TEXT = "Сохраните закладки перед удалением аккаунта."
    DELETION_SAVE_BOOKMARKS = "Сохранить закладки"
    DELETION_ALREADY = "Запрос на удаление уже существует."
    DELETION_CANCELED = "Запрос на удаление отменён"

    # ---------------------------------------------------------------- channels
    CHANNELS_TITLE = "Каналы"
    CHANNELS_SEARCH = "Поиск каналов"
    CHANNELS_CREATE = "Создать канал"
    CHANNELS_ALL = "Все каналы"
    CHANNELS_SUBSCRIBED = "Только с подпиской"
    CHANNELS_SUBSCRIBERS = "Подписчики"
    CHANNELS_ADMINS = "Администраторы"
    CHANNELS_BLOCKS = "Блоклист"
    CHANNELS_HIDDEN = "Скрытые каналы"
    CHANNELS_MANAGE = "Перейти к управлению"
    CHANNELS_EDIT = "Управление каналом"
    CHANNELS_ADD_ARTICLE = "Добавить запись…"
    CHANNELS_DELETE = "Удалить канал"
    CHANNELS_CREATED = "Канал создан"
    CHANNELS_SAVED = "Изменения сохранены"
    CHANNELS_TITLE_HINT = "Название (10–60 символов)"
    CHANNELS_DESCRIPTION_HINT = "Описание (10–60 символов)"
    CHANNELS_INVALID_TITLE = "Неверное название канала: минимум 10 и максимум 60 символов."
    CHANNELS_COMMENTS = "Разрешить комментарии"
    CHANNELS_SUGGESTIONS = "Разрешить предложенные записи"
    CHANNELS_WIDGET = "Виджет в озвучке"
    CHANNELS_EMPTY_ADMINS = "Похоже, нет ни одного администратора"
    CHANNELS_EMPTY_BLOCKS = "Похоже, нет ни одного заблокированного пользователя"
    CHANNELS_EMPTY_SUBSCRIBERS = "Похоже, нет ни одного подписчика"
    CHANNELS_EMPTY_OWN = "Вы не подписаны ни на один из каналов, которыми управляете"
    CHANNELS_NOT_FOUND = "Канал не найден"
    CHANNELS_HIDDEN_STATE = "Канал скрыт"

    # ---------------------------------------------------------------- articles
    ARTICLES_TITLE = "Записи"
    ARTICLE_TITLE = "Запись"
    ARTICLE_CREATE = "Новая запись"
    ARTICLE_EDIT = "Редактирование записи"
    ARTICLE_EXPAND = "Показать ещё"
    ARTICLE_COLLAPSE = "Скрыть до предпросмотра"
    ARTICLE_DELETE = "Удалить запись?"
    ARTICLE_HIDE = "Скрыть запись"
    ARTICLE_SEND = "Опубликовать"
    ARTICLE_DRAFT = "Черновик"
    ARTICLE_PREVIEW = "Предпросмотр"
    ARTICLE_ALMOST_READY = "Запись почти готова!"
    ARTICLE_TITLE_FIELD = "Заголовок"
    ARTICLE_TEXT_FIELD = "Текст записи"
    ARTICLE_COVER = "Обложка"
    ARTICLE_UNSUPPORTED = "Этот блок не поддерживается этой версией anx-desktop…"
    ARTICLE_NOT_FOUND = "Запись не найдена"
    ARTICLE_DELETED = "Запись удалена"
    ARTICLE_SUGGEST = "Предложение записи"
    ARTICLE_SUGGESTIONS = "Предложенные записи"
    ARTICLE_REPOSTS = "Репосты"
    ARTICLE_COMMENTS = "Комментарии"
    ARTICLE_WRITE_COMMENT = "Написать"
    ARTICLE_COMMENT_HINT = "Оставьте комментарий…"
    ARTICLE_SPOILER = "Спойлер"
    ARTICLE_RULES = "Правила"
    ARTICLE_LIKE = "За"
    ARTICLE_DISLIKE = "Против"
    ARTICLE_PUBLISHED = "Запись опубликована"
    ARTICLE_DRAFT_SAVED = "Черновик сохранён"
    ARTICLE_COMMENT_SENT = "Комментарий отправлен"
    ARTICLE_BLOCK_PARAGRAPH = "Абзац"
    ARTICLE_BLOCK_HEADER = "Заголовок"
    ARTICLE_BLOCK_LIST = "Список"
    ARTICLE_BLOCK_QUOTE = "Цитата"
    ARTICLE_BLOCK_MEDIA = "Медиа"
    ARTICLE_BLOCK_EMBED = "Встраивание"
    ARTICLE_BLOCK_DIVIDER = "Разделитель"

    # ------------------------------------------------------------- collections
    COLLECTIONS_TITLE = "Коллекции"
    COLLECTIONS_SEARCH = "Поиск коллекций"
    COLLECTIONS_CREATE = "Создать коллекцию"
    COLLECTIONS_MY = "Мои коллекции"
    COLLECTIONS_FAVORITE = "Избранные"
    COLLECTIONS_SORT = "Сортировка"
    COLLECTIONS_FAVORITES_COUNT = "{count} в избранном"
    COLLECTIONS_COMMENTS_COUNT = "{count} комментариев"
    COLLECTIONS_ADD_FAVORITE = "Добавить в закладки"
    COLLECTIONS_IN_FAVORITE = "В закладках"
    COLLECTIONS_EDIT = "Редактировать"
    COLLECTIONS_DELETE = "Удалить"
    COLLECTIONS_PRIVATE = "Приватная коллекция"
    COLLECTIONS_DELETED = "Коллекция удалена"
    COLLECTIONS_CREATED = "Коллекция создана"
    COLLECTIONS_EMPTY_MINE = "У вас пока нет коллекций"
    COLLECTIONS_EMPTY_HINT = "Создайте коллекцию и добавьте в неё любимые релизы."

    # --------------------------------------------------------------- history
    HISTORY_TITLE = "История просмотра"
    HISTORY_SUBTITLE = "Недавно просмотренное"
    HISTORY_EMPTY = "Вы ещё ничего не смотрели"
    HISTORY_EMPTY_HINT = "Начните смотреть релиз — он появится в истории."
    HISTORY_EPISODE = "{episode} · {type}"
    HISTORY_WATCHED_AT = "{date}"
    HISTORY_CLEAR = "Очистить историю"

    BOOKMARK_EMPTY_COLLECTIONS = "Добавляй коллекции в избранное…"
    BOOKMARK_EMPTY_HISTORY = "Здесь появится история просмотра."
    BOOKMARK_EMPTY_FAVORITES = "Добавляй понравившиеся аниме в избранное…"
    BOOKMARK_EMPTY_WATCHING = "Начни что-нибудь смотреть…"
    BOOKMARK_EMPTY_PLANNED = "Добавь релизы в список «В планах»…"
    BOOKMARK_EMPTY_COMPLETED = "Здесь появятся просмотренные релизы."
    BOOKMARK_EMPTY_HOLD = "Отложенные релизы появятся здесь."
    BOOKMARK_EMPTY_DROPPED = "Брошенные релизы появятся здесь."
    BOOKMARK_SORT_NEW = "От новых к старым"
    BOOKMARK_SORT_OLD = "От старых к новым"
    BOOKMARK_SORT_TITLE = "По названию А–Я"
    BOOKMARK_SORT_TITLE_DESC = "По названию Я–А"
    BOOKMARK_SORT_YEAR = "По году"
    BOOKMARK_RANDOM = "Случайный релиз"

    # ---------------------------------------------------------- notifications
    NOTIFICATIONS_TITLE = "Уведомления"
    NOTIFICATIONS_DELETE_ALL = "Удалить все"
    NOTIFICATIONS_FILTER = "Фильтр уведомлений"
    NOTIFICATIONS_EMPTY_HINT = "Здесь появятся новые серии, ответы и записи каналов."
    NOTIFICATIONS_DISABLED = "Уведомления отключены"
    NOTIFICATIONS_DISABLED_HINT = "Включите уведомления в настройках, чтобы получать новости."
    NOTIFICATIONS_PUSH = "Push-уведомления запрещены системой"
    NOTIFICATIONS_NEW_EPISODE = "Вышла новая серия"
    NOTIFICATIONS_NEW_ARTICLE = "Новая запись канала"
    NOTIFICATIONS_REPLY = "Новый ответ"
    NOTIFICATIONS_FRIEND = "Заявка в друзья"
    NOTIFICATIONS_ACHIEVEMENT = "Получен значок"
    NOTIFICATIONS_MARK_READ = "Отметить прочитанным"
    NOTIFICATIONS_SPOILER = "Уведомление может содержать спойлер."
    NOTIFICATIONS_SHOW = "Нажмите, чтобы прочитать"

    # ---------------------------------------------------------------- settings
    SETTINGS_TITLE = "Настройки"
    SETTINGS_DARK_THEME = "Тёмная тема"
    SETTINGS_THEME_LIGHT = "Выключена"
    SETTINGS_THEME_DARK = "Включена"
    SETTINGS_THEME_SYSTEM = "Как в системе"
    SETTINGS_THEME_DEEP_BLACK = "Глубокий чёрный"
    SETTINGS_THEME_HINT = "Тема применяется сразу, без перезапуска."
    SETTINGS_DEEP_BLACK_TODO = "Нет токена глубокого чёрного в 8.5.2 — отложено."
    SETTINGS_NOTIFICATIONS = "Уведомления"
    SETTINGS_NOTIFICATIONS_SUMMARY = "Серии, релизы, записи, комментарии, жалобы"
    SETTINGS_PLAYBACK = "Воспроизведение"
    SETTINGS_PLAYBACK_SUMMARY = "Плеер, качество, перемотка, автовоспроизведение"
    SETTINGS_APPEARANCE = "Внешний вид"
    SETTINGS_APPEARANCE_SUMMARY = "Вид отображения, вкладки, меню, формат времени"
    SETTINGS_DATA = "Данные и память"
    SETTINGS_DATA_SUMMARY = "Импорт и экспорт закладок, кэш"
    SETTINGS_ADS = "Реклама"
    SETTINGS_ADS_SUMMARY = "Управление рекламой"
    SETTINGS_ADVANCED = "Дополнительно"
    SETTINGS_ADVANCED_SUMMARY = "Экономия ресурсов, соединение, веб-кэш"
    SETTINGS_HELP = "Помощь"
    SETTINGS_RULES = "Правила сообщества"
    SETTINGS_UPDATE = "Проверить обновления"
    SETTINGS_REPORT_BUG = "Сообщить об ошибке"
    SETTINGS_REPORT_BUG_SENT = "Спасибо! Сообщение об ошибке отправлено."
    SETTINGS_VERSION = "Версия"
    SETTINGS_PROFILE = "Профиль"
    SETTINGS_PROFILE_SUMMARY = "Персонализация, приватность, безопасность"
    SETTINGS_ACCOUNT = "Аккаунт"
    SETTINGS_DEMO = "Демо-состояния"
    SETTINGS_DEMO_HINT = (
        "Clean-room переключатель для проверки loading/empty/error на всех экранах."
    )
    SETTINGS_VIEW_MODE = "Вид отображения релизов"
    SETTINGS_VIEW_LIST = "Списком"
    SETTINGS_VIEW_GRID = "Карточками"
    SETTINGS_COMPACT_MENU = "Компактный вид меню"
    SETTINGS_COMPACT_MENU_SUMMARY = (
        "Уменьшить размер основного меню и увеличить пространство для контента."
    )
    SETTINGS_HOME_DEFAULT = "Вкладка на главной по умолчанию"
    SETTINGS_BOOKMARKS_DEFAULT = "Вкладка в закладках по умолчанию"
    SETTINGS_CONTINUE = "Продолжить просмотр"
    SETTINGS_CONTINUE_SUMMARY = "Показывать последнюю серию в верхней панели"
    SETTINGS_TIME_FORMAT = "Формат времени просмотра"
    SETTINGS_TIME_SHORT = "Короткий"
    SETTINGS_TIME_HOURS = "Часы и минуты"
    SETTINGS_HIDE_WIDGETS = "Скрывать виджеты каналов"
    SETTINGS_AUTOPLAY = "Автовоспроизведение"
    SETTINGS_AUTOPLAY_SUMMARY = "Следующая серия запускается автоматически"
    SETTINGS_QUALITY = "Приоритет качества"
    SETTINGS_SEEK = "Время перемотки"
    SETTINGS_SEEK_5 = "5 секунд"
    SETTINGS_SEEK_10 = "10 секунд"
    SETTINGS_SEEK_15 = "15 секунд"
    SETTINGS_PLAYER = "Видеоплеер"
    SETTINGS_PLAYER_ASK = "Спрашивать"
    SETTINGS_PLAYER_EMBEDDED = "Встроенный"
    SETTINGS_PLAYER_WEB = "Веб-плеер"
    SETTINGS_PLAYER_ANIX = "АниксПлеер"
    SETTINGS_PLAYER_THIRD = "Сторонний"
    SETTINGS_REMEMBER_SOURCE = "Запоминать источник"
    SETTINGS_HORIZONTAL = "Только горизонтальное положение"
    SETTINGS_IMPORT = "Импорт закладок"
    SETTINGS_EXPORT = "Экспорт закладок"
    SETTINGS_IMPORT_OK = "Закладки импортированы"
    SETTINGS_EXPORT_OK = "Закладки экспортированы"
    SETTINGS_EXPORT_FORMAT = "Формат экспорта"
    SETTINGS_EXPORT_RU = "С русским названием"
    SETTINGS_EXPORT_ORIGINAL = "С оригинальным названием"
    SETTINGS_EXPORT_NO_TITLE = "Без названия"
    SETTINGS_CACHE = "Кэш изображений"
    SETTINGS_CACHE_USAGE = "Использовано {size}"
    SETTINGS_CACHE_LIMIT = "Лимит кэша"
    SETTINGS_CACHE_LIMITS = ("256 МБ", "512 МБ", "1 ГБ", "2 ГБ")
    SETTINGS_AD_ITEMS = ("Kodik", "Веб-плеер", "Interstitial", "Баннер")
    SETTINGS_CLEAR_CACHE = "Очистить кэш"
    SETTINGS_CLEAR_CACHE_CONFIRM = "Очистить кэш изображений?"
    SETTINGS_CACHE_CLEARED = "Кэш изображений очищен"
    SETTINGS_ECONOMY = "Режим экономии ресурсов"
    SETTINGS_ECONOMY_SUMMARY = "Меньше анимаций и фоновых запросов"
    SETTINGS_ALT_CONNECTION = "Альтернативное соединение"
    SETTINGS_ALT_CONNECTION_SUMMARY = "Использовать зеркальные адреса"
    SETTINGS_CLEAR_WEB = "Очистить веб-кэш"
    SETTINGS_CLEAR_WEB_WARNING = "Важно: черновик записи будет утерян."
    SETTINGS_CLEAR_WEB_CONFIRM = "Очистить веб-кэш?"
    SETTINGS_WEB_CLEARED = "Веб-кэш очищен"
    SETTINGS_PUSH_EPISODES = "Уведомления о сериях"
    SETTINGS_PUSH_RELEASES = "Уведомления о релизах"
    SETTINGS_PUSH_ARTICLES = "Записи каналов"
    SETTINGS_PUSH_COMMENTS = "Ответы и комментарии"
    SETTINGS_PUSH_REPORTS = "Уведомления о жалобах"
    SETTINGS_SYSTEM_CATEGORIES = "Категории уведомлений"
    SETTINGS_ABOUT = "О приложении"
    SETTINGS_ACCESSIBILITY = "Доступность"
    SETTINGS_REDUCE_MOTION = "Уменьшить движение"
    SETTINGS_REDUCE_MOTION_SUMMARY = "Отключить scale/bounce, оставить только fade"
    SETTINGS_UI_SCALE = "Масштаб интерфейса"
    SETTINGS_UI_SCALE_HINT = "Наследуется от системного масштаба (100/125/150%)."
    SETTINGS_DEMO_APPLIED = "Демо-состояние переключено"
    SETTINGS_NOT_AVAILABLE = "Раздел не подключён в clean-room сборке."
    SETTINGS_SHORTCUTS = (
        "Ctrl+K — поиск · Esc — назад · F5 — обновить · "
        "Space — play/pause · ←/→ — перемотка · F — полный экран"
    )
    SETTINGS_GROUPS = (
        "Тёмная тема",
        "Уведомления",
        "Воспроизведение",
        "Внешний вид",
        "Данные и память",
        "Реклама",
        "Дополнительно",
        "Помощь",
        "Правила сообщества",
        "Проверить обновления",
        "Сообщить об ошибке",
        "О приложении",
    )

    # ------------------------------------------------------------------- auth
    AUTH_TITLE = "Авторизация"
    AUTH_WELCOME = "С возвращением"
    AUTH_WELCOME_HINT = "Войдите, чтобы продолжить"
    AUTH_SIGN_IN_WITH = "Войти с помощью"
    AUTH_SIGN_UP_WITH = "Регистрация с помощью"
    AUTH_EMAIL_OR_NICK = "Почта или никнейм"
    AUTH_PASSWORD = "Пароль"
    AUTH_SHOW_PASSWORD = "Показать пароль"
    AUTH_HIDE_PASSWORD = "Скрыть пароль"
    AUTH_PASSWORD_REPEAT = "Повторите пароль"
    AUTH_LOGIN = "Войти"
    AUTH_FORGOT = "Забыли пароль?"
    AUTH_SKIP = "Пропустить"
    AUTH_NO_ACCOUNT = "Нет профиля?"
    AUTH_HAS_ACCOUNT = "Уже есть профиль?"
    AUTH_REGISTER = "Регистрация"
    AUTH_CREATE_PROFILE = "Создать профиль"
    AUTH_CREATE = "Регистрация"
    AUTH_QR = "QR-код с телефона"
    AUTH_QR_FULL = "Вход с телефона"
    AUTH_YANDEX = "Яндекс"
    AUTH_VK = "ВКонтакте"
    AUTH_TELEGRAM = "Telegram"
    AUTH_GOOGLE = "Google"
    AUTH_EMAIL = "Почта или никнейм"
    AUTH_ALMOST_DONE = "Почти готово"
    AUTH_NICK = "Никнейм"
    AUTH_EMAIL_FIELD = "Email"
    AUTH_CONSENT_1 = (
        "Я принимаю Пользовательское соглашение и даю Согласие на обработку "
        "персональных данных…"
    )
    AUTH_CONSENT_2 = (
        "Я даю Согласие на обработку персональных данных, разрешенных субъектом…"
    )
    AUTH_CONSENT_REQUIRED = "Для регистрации нужно принять оба согласия."
    AUTH_VERIFY = "Подтвердите почту"
    AUTH_VERIFY_HINT = "Введите код из письма"
    AUTH_VERIFY_ACTION = "Подтвердить"
    AUTH_RESEND = "Отправить код повторно"
    AUTH_SPAM = "Код всё ещё не приходит? Проверьте папку «Спам»"
    AUTH_RESTORE_TITLE = "Восстановление пароля"
    AUTH_RESTORE_HINT = "Укажите почту или никнейм и новый пароль"
    AUTH_CONTINUE = "Продолжить"
    AUTH_ERROR_EMPTY = "Заполните все поля"
    AUTH_ERROR_INVALID = "Неверный логин или пароль"
    AUTH_ERROR_EMAIL = "Введите корректный email"
    AUTH_ERROR_SHORT = "Пароль слишком короткий"
    AUTH_ERROR_NICK = "Никнейм указан некорректно"
    AUTH_ERROR_TAKEN = "Никнейм уже занят"
    AUTH_ERROR_TERMS = "Примите оба согласия"
    AUTH_GUEST = "Вы вошли как гость"
    AUTH_UNAVAILABLE = "Вход через {provider} временно недоступен"
    AUTH_QR_SCAN = "Наведите камеру телефона на QR-код"
    AUTH_QR_OPEN = "Откройте ссылку в мобильном приложении"
    AUTH_QR_PIN = "Введите на телефоне этот код:"
    AUTH_QR_REFRESH = "Новый QR-код"
    AUTH_QR_OTHER = "Другие способы входа"
    AUTH_QR_CONFIRM_TITLE = "Войти на другом устройстве?"
    AUTH_QR_CONFIRM_ACCOUNT = "Аккаунт"
    AUTH_QR_CONFIRM_DEVICE = "Устройство"
    AUTH_QR_CONFIRM_CODE = "Введите код с экрана устройства"
    AUTH_QR_CONFIRM_WARNING = (
        "Вводите код только если он виден на вашем устройстве."
    )
    AUTH_QR_ALLOW = "Разрешить вход"
    AUTH_QR_DECLINE = "Отклонить"
    AUTH_QR_CONFIRMED = "Вход подтверждён"
    AUTH_QR_DECLINED = "Вход отклонён"
    AUTH_QR_EXPIRED = "QR-код устарел"
    AUTH_QR_BLOCKED = "Слишком много попыток"
    AUTH_QR_BLOCKED_HINT = "Код введён неверно слишком много раз. Мы показали новый QR-код."
    AUTH_QR_STATUS = "Ожидаем подтверждение на телефоне…"
    AUTH_PROVIDER_YANDEX = "Яндекс"
    AUTH_PROVIDER_VK = "ВКонтакте"
    AUTH_PROVIDER_TELEGRAM = "Telegram"
    AUTH_PROVIDER_GOOGLE = "Google"
    AUTH_QR_LINKED = "Ссылка открыта на телефоне — введите на нём код"
    AUTH_QR_CODE = "Код для телефона"
    AUTH_LOGOUT = "Выйти из учётной записи"

    # --------------------------------------------------------------- comments
    COMMENTS_TITLE = "Комментарии"
    COMMENTS_SORT = "Сортировка"
    COMMENTS_REPLY = "Ответить"
    COMMENTS_DELETED = "Комментарий удалён"
    COMMENTS_SPOILER_WARNING = "Комментарий может содержать спойлер."
    COMMENTS_SHOW_SPOILER = "Нажмите, чтобы прочитать"
    COMMENTS_INPUT_HINT = "Ваш комментарий"
    COMMENTS_SHOW_REPLIES = "Показать {count} ответов"
    COMMENTS_EDITED = "изменено"
    COMMENTS_SEND = "Отправить"
    COMMENTS_AUTH_REQUIRED = "Войдите, чтобы оставить комментарий"
    COMMENTS_VOTES = "Голоса"
    COMMENTS_RULES = "Правила"
    COMMENTS_SPOILER_MARK = "Спойлер"

    # ---------------------------------------------------------------- misc
    SCHEDULE_TITLE = "Расписание"
    SCHEDULE_EMPTY = "На этой неделе релизов нет"
    UPDATES_TITLE = "Обновления серий"
    UPDATES_EMPTY = "Новых серий пока нет"
    FRIENDS_TITLE = "Друзья"
    FRIENDS_REQUESTS = "Заявки"
    FRIENDS_RECOMMENDATIONS = "Рекомендации"
    FRIENDS_EMPTY = "У вас пока нет друзей"
    BLOCKLIST_TITLE = "Блоклист"
    BLOCKLIST_EMPTY = "В блоклисте никого нет"
    UNBLOCK = "Разблокировать"
    RANDOM_EMPTY = "Не удалось выбрать случайный релиз"
    TEAM_TITLE = "Роли"
    ABOUT_TITLE = "О приложении"
    ABOUT_TEXT = (
        "Clean-room десктопный интерфейс по визуальному гайду 8.5.2 и "
        "информационной архитектуре 11 BETA 2. Все данные демонстрационные."
    )
    ASSET_DISCLAIMER = "Иконки отрисованы с нуля; постеры заменены нейтральными плейсхолдерами."
    RULES_TEXT = (
        "Уважайте собеседников, не публикуйте спойлеры без пометки и не "
        "распространяйте запрещённый контент."
    )
    HELP_TEXT = (
        "Это демонстрационная сборка интерфейса. Сетевые операции отключены, "
        "а коннектор API подключается отдельным слоем."
    )
    UPDATE_TEXT = "У вас установлена последняя демонстрационная версия интерфейса."
    UPDATE_CHECKED = "Обновлений нет"
    CREATE_ARTICLE_TITLE = "Создать запись"
    CREATE_CHANNEL_TITLE = "Создать канал"
    CREATE_ARTICLE_TEXT = "Название записи"
    CREATE_ARTICLE_BODY = "Текст"
    CREATE_CHANNEL_NAME = "Название канала"
    CREATE_CHANNEL_DESCRIPTION = "Описание"
    CREATE_DONE = "Готово"
    DIALOG_TITLE_PREFIX = ""
    SELECT_ALL = "Выбрать все"
    CLEAR = "Очистить"

    # --------------------------------------------------------------- a11y/tools
    TOOLTIP_THEME = "Переключить светлую/тёмную тему"
    TOOLTIP_REFRESH = "Обновить (F5)"
    TOOLTIP_SEARCH = "Поиск (Ctrl+K)"
    TOOLTIP_NOTIFICATIONS = "Уведомления"
    TOOLTIP_PROFILE = "Профиль"
    TOOLTIP_SETTINGS = "Настройки"
    TOOLTIP_CREATE = "Создать запись или канал"
    TOOLTIP_MORE = "Дополнительно"
    TOOLTIP_CLOSE = "Закрыть"
    TOOLTIP_PLAY = "Воспроизвести (Space)"
    TOOLTIP_FULLSCREEN = "Полный экран (F)"
    TOOLTIP_BACK = "Назад (Esc)"
    TOOLTIP_FORWARD = "Вперёд (Alt+→)"
    TOOLTIP_SIDEBAR = "Свернуть/развернуть меню"
    TOOLTIP_FILTER = "Фильтр (Ctrl+Shift+F)"
    TOOLTIP_NEXT = "Следующая серия"
    TOOLTIP_PREV = "Предыдущая серия"
    TOOLTIP_VOLUME = "Громкость (↑/↓)"
    TOOLTIP_PIP = "Картинка в картинке"
    TOOLTIP_LOCK = "Заблокировать контролы"

    # --------------------------------------------------------------- date/time
    MONTHS = _MONTHS = (
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    )
